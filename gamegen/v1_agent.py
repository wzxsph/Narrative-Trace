from __future__ import annotations

import json
import re
import subprocess
from copy import deepcopy
from pathlib import Path
from typing import Any, Literal

from jsonschema import Draft202012Validator

from .agent_graph import (
    AgentRunError,
    build_generation_plan,
    build_state_schema_design,
    run_generation_agent,
)
from .content_pack import LOOP_PACKAGES_ROOT, load_content_pack
from .decision_receipt import (
    DecisionReceiptError,
    artifact_digest,
    create_decision_receipt,
    validate_decision_receipt,
    write_receipt,
)
from .g5 import run_g5
from .gates import pack_input_digest, run_pack_gates
from .kernel_contract import ROOT
from .model_output_archive import assert_no_unredacted_secrets, redact_sample_text
from .scene_blueprint import build_scene_blueprint_design, validate_scene_blueprint_design
from .state_schema_design import validate_state_schema_design
from .v1_migration import export_v1_content_pack


PIPELINE_SCHEMA_VERSION = "narrative_generation_pipeline_v1"
BRIEF_ARTIFACT_VERSION = "narrative_brief_artifact_v1"
RELEASE_CANDIDATE_VERSION = "narrative_release_candidate_v1"
LOOP_REF_RE = re.compile(r"^(?P<id>[a-z][a-z0-9_.-]*)@(?P<version>[0-9]+\.[0-9]+\.[0-9]+)$")
GateThrough = Literal["G4", "G5"]


class V1AgentError(RuntimeError):
    pass


def prepare_pipeline(
    brief_path: str | Path,
    workspace: str | Path,
    *,
    loop_ref: str = "investigation@1.0.0",
    provider: str = "offline",
    pack_version: str = "1.0.0",
    max_repair_attempts: int = 1,
) -> dict[str, Any]:
    root = Path(workspace)
    artifacts = root / "artifacts"
    decisions = root / "decisions"
    artifacts.mkdir(parents=True, exist_ok=True)
    decisions.mkdir(parents=True, exist_ok=True)
    brief = load_json(Path(brief_path), "brief")
    validate_brief(brief)
    loop_package = load_loop_reference(loop_ref)
    if loop_package["id"] != "investigation":
        raise V1AgentError("V1 generator currently has a deterministic compiler only for the investigation loop")
    brief_artifact = {
        "schema_version": BRIEF_ARTIFACT_VERSION,
        "brief": brief,
        "loop_package": loop_package,
        "pack_version": pack_version,
    }
    write_json(artifacts / "brief.json", brief_artifact)
    pipeline = {
        "schema_version": PIPELINE_SCHEMA_VERSION,
        "phase": "awaiting_brief_approval",
        "provider": provider,
        "pack_version": pack_version,
        "max_repair_attempts": max_repair_attempts,
        "loop_package": loop_package,
        "artifacts": {"brief": "artifacts/brief.json"},
        "decisions": {},
        "digests": {"brief": artifact_digest(artifacts / "brief.json")},
    }
    write_pipeline(root, pipeline)
    return pipeline


def approve_pipeline_checkpoint(
    workspace: str | Path,
    checkpoint: str,
    *,
    actor: str,
    notes: str = "",
    decision: str = "approved",
    experimental_opt_in: bool = False,
    subject_path: str | Path | None = None,
    decided_at: str | None = None,
) -> dict[str, Any]:
    root = Path(workspace)
    pipeline = load_pipeline(root)
    subject = Path(subject_path) if subject_path else checkpoint_subject(root, checkpoint)
    receipt = create_decision_receipt(
        checkpoint=checkpoint,  # type: ignore[arg-type]
        subject_path=subject,
        actor=actor,
        decision=decision,  # type: ignore[arg-type]
        notes=notes,
        experimental_opt_in=experimental_opt_in,
        decided_at=decided_at,
    )
    try:
        assert_no_unredacted_secrets(json.dumps(receipt, ensure_ascii=False))
    except ValueError as exc:
        raise V1AgentError("DecisionReceipt contains sensitive data; use a non-secret actor/notes value") from exc
    receipt_path = root / "decisions" / f"{checkpoint}.json"
    write_receipt(receipt_path, receipt)
    pipeline.setdefault("decisions", {})[checkpoint] = receipt_path.relative_to(root).as_posix()
    write_pipeline(root, pipeline)
    return receipt


def advance_pipeline(workspace: str | Path, *, gate_through: GateThrough = "G5") -> dict[str, Any]:
    root = Path(workspace)
    pipeline = load_pipeline(root)
    phase = pipeline["phase"]
    if phase == "awaiting_brief_approval":
        require_receipt(root, pipeline, "brief")
        build_blueprint_artifacts(root, pipeline)
        pipeline["phase"] = "awaiting_blueprint_approval"
        write_pipeline(root, pipeline)
        return pipeline
    if phase == "awaiting_blueprint_approval":
        require_receipt(root, pipeline, "brief")
        require_receipt(root, pipeline, "blueprint")
        compile_content_pack(root, pipeline, gate_through=gate_through)
        return load_pipeline(root)
    if phase == "gates_incomplete":
        run_and_record_gates(root, pipeline, gate_through=gate_through)
        return load_pipeline(root)
    if phase in {"awaiting_release_approval", "released"}:
        return pipeline
    raise V1AgentError(f"Unsupported pipeline phase: {phase}")


def build_release_bundle(
    workspace: str | Path,
    output: str | Path,
    *,
    bundle_format: Literal["static", "worker"] = "static",
) -> dict[str, Any]:
    root = Path(workspace)
    pipeline = load_pipeline(root)
    if pipeline.get("phase") not in {"awaiting_release_approval", "released"}:
        raise V1AgentError("Content pack has not completed G1–G5")
    require_receipt(root, pipeline, "release")
    candidate = load_json(root / pipeline["artifacts"]["release_candidate"], "release candidate")
    context = load_content_pack(root)
    current_digest = pack_input_digest(context)
    if candidate.get("pack_input_digest") != current_digest:
        raise V1AgentError("Release candidate is stale: content pack digest changed after approval subject was created")
    results = run_pack_gates(root, through="G5", g5_runner=run_g5)
    if [item.status for item in results] != ["passed"] * 5:
        raise V1AgentError("Release bundle blocked because G1–G5 no longer pass")

    output_path = Path(output)
    if bundle_format == "static":
        from scripts.build_static_bundle import build_static_bundle

        report = build_static_bundle(root, output_path)
    else:
        command = [
            "node",
            str(ROOT / "scripts" / "build_game_worker_bundle.mjs"),
            "--pack",
            str(root),
            "--output",
            str(output_path),
        ]
        completed = subprocess.run(command, cwd=ROOT, check=False, capture_output=True, text=True)
        if completed.returncode != 0:
            raise V1AgentError(f"Worker bundle failed: {redact_sample_text(completed.stderr).strip()}")
        report = json.loads(completed.stdout)
    bundle_record = {
        "schema_version": "narrative_release_bundle_record_v1",
        "format": bundle_format,
        "pack_input_digest": current_digest,
        "release_receipt_digest": artifact_digest(root / "decisions" / "release.json"),
        "output": output_path.name,
        "files_or_routes": len(report.get("files", report.get("routes", []))),
    }
    write_json(root / "artifacts" / "release_bundle.json", bundle_record)
    pipeline["phase"] = "released"
    pipeline["artifacts"]["release_bundle"] = "artifacts/release_bundle.json"
    write_pipeline(root, pipeline)
    return bundle_record


def build_blueprint_artifacts(root: Path, pipeline: dict[str, Any]) -> None:
    brief_artifact = load_json(root / pipeline["artifacts"]["brief"], "brief artifact")
    brief = brief_artifact["brief"]
    plan = build_generation_plan(brief)
    state_design = build_state_schema_design(brief, plan)
    state_errors = [message for message in validate_state_schema_design(state_design) if message.level == "error"]
    if state_errors:
        raise V1AgentError("State design failed before blueprint: " + "; ".join(item.message for item in state_errors))
    blueprint = build_scene_blueprint_design(brief, plan, state_design)
    blueprint_errors = [
        message
        for message in validate_scene_blueprint_design(blueprint, plan, state_design)
        if message.level == "error"
    ]
    if blueprint_errors:
        raise V1AgentError("Blueprint failed validation: " + "; ".join(item.message for item in blueprint_errors))
    write_json(root / "artifacts" / "generation_plan.json", plan)
    write_json(root / "artifacts" / "state_schema_design.json", state_design)
    write_json(root / "artifacts" / "scene_blueprint.json", blueprint)
    pipeline["artifacts"].update(
        {
            "generation_plan": "artifacts/generation_plan.json",
            "state_schema_design": "artifacts/state_schema_design.json",
            "scene_blueprint": "artifacts/scene_blueprint.json",
        }
    )
    pipeline["digests"].update(
        {
            "generation_plan": artifact_digest(root / "artifacts" / "generation_plan.json"),
            "state_schema_design": artifact_digest(root / "artifacts" / "state_schema_design.json"),
            "scene_blueprint": artifact_digest(root / "artifacts" / "scene_blueprint.json"),
        }
    )


def compile_content_pack(root: Path, pipeline: dict[str, Any], *, gate_through: GateThrough) -> None:
    brief_artifact = load_json(root / pipeline["artifacts"]["brief"], "brief artifact")
    brief = brief_artifact["brief"]
    compat = root / "compat" / "v0"
    temp_brief = root / "artifacts" / "_legacy_brief.json"
    write_json(temp_brief, brief)
    try:
        state = run_generation_agent(
            temp_brief,
            compat,
            provider=pipeline["provider"],
            max_repair_attempts=int(pipeline["max_repair_attempts"]),
        )
    except AgentRunError as exc:
        raise V1AgentError(str(exc)) from exc
    finally:
        temp_brief.unlink(missing_ok=True)
    if state.game is None:
        raise V1AgentError("Compatibility compiler returned no game")
    staged_blueprint = artifact_digest(root / pipeline["artifacts"]["scene_blueprint"])
    compiled_blueprint = artifact_digest(compat / "scene_blueprint.json")
    if staged_blueprint != compiled_blueprint:
        raise V1AgentError("Deterministic compiler blueprint differs from the approved artifact")

    sanitize_tree(compat, root)
    (compat / "DEPRECATED.md").write_text(
        "# V0 compatibility projection\n\nRead-only V1.0 compatibility output. Removal requires separate V1.1 approval.\n",
        encoding="utf-8",
    )
    creative_names = [
        "generation_plan.json",
        "state_schema_design.json",
        "scene_blueprint.json",
        "scene_artifacts.json",
        "review_issues.json",
        "review_issue_policy.json",
        "agent_trace.jsonl",
    ]
    if (compat / "llm_scene_review.json").exists():
        creative_names.append("llm_scene_review.json")
    for name in creative_names:
        copy_redacted(compat / name, root / "artifacts" / name, root)
        pipeline["artifacts"][Path(name).stem] = f"artifacts/{name}"

    sanitized_game = sanitize_value(deepcopy(state.game), root)
    extra_paths = sorted(
        {
            *[f"artifacts/{name}" for name in creative_names],
            "artifacts/brief.json",
            "decisions/brief.json",
            "decisions/blueprint.json",
        }
    )
    export_v1_content_pack(
        sanitized_game,
        root,
        loop_package=pipeline["loop_package"],
        pack_version=pipeline["pack_version"],
        authorship="agent_assisted",
        extra_provenance_paths=extra_paths,
        trace_event="compiled_v1_content_pack",
    )
    pipeline["phase"] = "gates_incomplete"
    pipeline["artifacts"].update(
        {
            "pack": "pack.json",
            "game": "game.json",
            "state_registry": "state_registry.json",
            "provenance": "provenance/manifest.json",
            "legacy_projection": "compat/v0/game.json",
        }
    )
    write_pipeline(root, pipeline)
    run_and_record_gates(root, pipeline, gate_through=gate_through)


def run_and_record_gates(root: Path, pipeline: dict[str, Any], *, gate_through: GateThrough) -> None:
    results = run_pack_gates(root, through=gate_through, g5_runner=run_g5)
    report = {
        "schema_version": "narrative_gate_chain_report_v1",
        "results": [result.to_dict() for result in results],
    }
    write_json(root / "verification" / f"g1-{gate_through.lower()}.json", report)
    if any(result.status != "passed" for result in results):
        pipeline["phase"] = "gates_failed"
        write_pipeline(root, pipeline)
        failed = next(result for result in results if result.status != "passed")
        raise V1AgentError(f"{failed.gate_id} failed for generated content pack")
    if gate_through != "G5":
        pipeline["phase"] = "gates_incomplete"
        write_pipeline(root, pipeline)
        return
    context = load_content_pack(root)
    report_path = root / "verification" / "g1-g5.json"
    candidate = {
        "schema_version": RELEASE_CANDIDATE_VERSION,
        "pack_id": context.manifest["pack_id"],
        "pack_version": context.manifest["version"],
        "pack_input_digest": pack_input_digest(context),
        "gate_report_digest": artifact_digest(report_path),
        "gates": [result.gate_id for result in results],
        "status": "ready_for_release_approval",
    }
    write_json(root / "artifacts" / "release_candidate.json", candidate)
    pipeline["phase"] = "awaiting_release_approval"
    pipeline["artifacts"]["gate_report"] = "verification/g1-g5.json"
    pipeline["artifacts"]["release_candidate"] = "artifacts/release_candidate.json"
    pipeline["digests"]["pack_input"] = candidate["pack_input_digest"]
    pipeline["digests"]["release_candidate"] = artifact_digest(root / "artifacts" / "release_candidate.json")
    write_pipeline(root, pipeline)


def require_receipt(root: Path, pipeline: dict[str, Any], checkpoint: str) -> dict[str, Any]:
    subject = checkpoint_subject(root, checkpoint)
    receipt_path = root / "decisions" / f"{checkpoint}.json"
    experimental = checkpoint == "brief" and pipeline["loop_package"]["tier"] == "experimental"
    try:
        return validate_decision_receipt(
            receipt_path,
            checkpoint=checkpoint,  # type: ignore[arg-type]
            subject_path=subject,
            require_experimental_opt_in=experimental,
        )
    except DecisionReceiptError as exc:
        raise V1AgentError(str(exc)) from exc


def checkpoint_subject(root: Path, checkpoint: str) -> Path:
    mapping = {
        "brief": root / "artifacts" / "brief.json",
        "blueprint": root / "artifacts" / "scene_blueprint.json",
        "release": root / "artifacts" / "release_candidate.json",
    }
    if checkpoint not in mapping:
        raise V1AgentError(f"Checkpoint requires an explicit subject: {checkpoint}")
    if not mapping[checkpoint].is_file():
        raise V1AgentError(f"Checkpoint subject does not exist yet: {mapping[checkpoint]}")
    return mapping[checkpoint]


def load_loop_reference(reference: str) -> dict[str, Any]:
    match = LOOP_REF_RE.fullmatch(reference)
    if not match:
        raise V1AgentError("Loop reference must be exact, for example investigation@1.0.0")
    loop_id = match.group("id")
    version = match.group("version")
    major = version.split(".", 1)[0]
    loop_root = LOOP_PACKAGES_ROOT / loop_id / f"v{major}"
    loop = load_json(loop_root / "loop.json", "loop package")
    schema = load_json(ROOT / "loop_packages" / "loop-package.schema.json", "loop package schema")
    errors = sorted(Draft202012Validator(schema).iter_errors(loop), key=lambda item: list(item.absolute_path))
    if errors:
        raise V1AgentError("Installed loop package is invalid: " + "; ".join(error.message for error in errors))
    if loop.get("id") != loop_id or loop.get("version") != version:
        raise V1AgentError(f"Exact loop package is not installed: {reference}")
    return {
        "id": loop_id,
        "version": version,
        "tier": loop["tier"],
        "verification_status": loop["verification"]["status"],
    }


def validate_brief(brief: dict[str, Any]) -> None:
    try:
        project = brief["project"]
        world = brief["world"]
        required = [project["id"], project["title"], project["theme_question"], world["interface"]]
    except (KeyError, TypeError) as exc:
        raise V1AgentError("Brief must include project id/title/theme_question and world.interface") from exc
    if not all(isinstance(value, str) and value for value in required):
        raise V1AgentError("Brief identity fields must be non-empty strings")


def load_pipeline(root: Path) -> dict[str, Any]:
    pipeline = load_json(root / "pipeline.json", "pipeline")
    if pipeline.get("schema_version") != PIPELINE_SCHEMA_VERSION:
        raise V1AgentError("Unsupported pipeline schema")
    return pipeline


def write_pipeline(root: Path, pipeline: dict[str, Any]) -> None:
    write_json(root / "pipeline.json", pipeline)


def load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise V1AgentError(f"Missing {label}: {path}") from exc
    except json.JSONDecodeError as exc:
        raise V1AgentError(f"Invalid {label} JSON: {path}") from exc
    if not isinstance(value, dict):
        raise V1AgentError(f"{label} must be a JSON object")
    return value


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def copy_redacted(source: Path, destination: Path, workspace: Path) -> None:
    text = source.read_text(encoding="utf-8")
    text = sanitize_text(text, workspace)
    assert_no_unredacted_secrets(text)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(text if text.endswith("\n") else text + "\n", encoding="utf-8")


def sanitize_tree(root: Path, workspace: Path) -> None:
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        sanitized = sanitize_text(text, workspace)
        assert_no_unredacted_secrets(sanitized)
        path.write_text(sanitized, encoding="utf-8")


def sanitize_value(value: Any, workspace: Path) -> Any:
    if isinstance(value, str):
        return sanitize_text(value, workspace)
    if isinstance(value, list):
        return [sanitize_value(item, workspace) for item in value]
    if isinstance(value, dict):
        return {key: sanitize_value(item, workspace) for key, item in value.items()}
    return value


def sanitize_text(text: str, workspace: Path) -> str:
    redacted = text.replace(str(workspace.resolve()), "<WORKSPACE>")
    redacted = redacted.replace(str(ROOT.resolve()), "<PROJECT_ROOT>")
    return redact_sample_text(redacted)
