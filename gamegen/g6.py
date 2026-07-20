from __future__ import annotations

import json
from copy import deepcopy
from datetime import date
from pathlib import Path
from typing import Any, Iterable

from jsonschema import Draft202012Validator

from .content_pack import ContentPackLoadError, load_content_pack, resolve_relative_file
from .decision_receipt import artifact_digest, validate_decision_receipt
from .gates import GateMessage, GateResult, pack_input_digest
from .kernel_contract import ROOT, canonical_digest, validate_kernel_document


class G6ConfigError(RuntimeError):
    pass


def run_g6(pack_dir: str | Path, batch_path: str | Path) -> GateResult:
    try:
        context = load_content_pack(pack_dir)
    except ContentPackLoadError as exc:
        raise G6ConfigError(str(exc)) from exc
    batch = load_object(batch_path, "playtest batch")
    metrics = context.loop_experience_metrics.get("metrics")
    if not isinstance(metrics, list) or not metrics:
        raise G6ConfigError("Loop package experience metrics are missing")
    entrypoints = context.loop_manifest.get("entrypoints", {})
    try:
        batch_schema_path = resolve_relative_file(
            context.loop_root,
            entrypoints.get("playtest_batch_schema"),
            "loop.entrypoints.playtest_batch_schema",
        )
        record_schema_path = resolve_relative_file(
            context.loop_root,
            entrypoints.get("playtest_record_schema"),
            "loop.entrypoints.playtest_record_schema",
        )
    except ContentPackLoadError as exc:
        raise G6ConfigError(str(exc)) from exc
    batch_schema = load_object(batch_schema_path, "playtest batch schema")
    record_schema = load_object(record_schema_path, "playtest record schema")
    current_pack_digest = pack_input_digest(context)
    digest = canonical_digest(
        {"batch": batch, "pack_input_digest": current_pack_digest, "experience_metrics": metrics}
    )
    result = GateResult("G6", digest)

    validation_schema = deepcopy(batch_schema)
    validation_schema["properties"]["participants"]["items"] = record_schema
    validator = Draft202012Validator(validation_schema)
    for error in sorted(validator.iter_errors(batch), key=lambda item: list(item.absolute_path)):
        location = ".".join(str(part) for part in error.absolute_path) or "<root>"
        result.errors.append(GateMessage("playtest.schema", f"batch.{location}", error.message))
    manifest = context.manifest
    loop_ref = manifest.get("loop_package", {})
    identity_checks = (
        ("pack_id", manifest.get("pack_id")),
        ("pack_version", manifest.get("version")),
        ("pack_input_digest", current_pack_digest),
    )
    for field, expected in identity_checks:
        if batch.get(field) != expected:
            result.errors.append(
                GateMessage("playtest.subject_mismatch", f"batch.{field}", "Batch is not bound to this content-pack build")
            )
    if batch.get("loop_package") != {"id": loop_ref.get("id"), "version": loop_ref.get("version")}:
        result.errors.append(
            GateMessage("playtest.loop_mismatch", "batch.loop_package", "Batch loop package does not match pack.json")
        )
    try:
        date.fromisoformat(batch.get("session_date", ""))
    except (TypeError, ValueError):
        result.errors.append(
            GateMessage("playtest.session_date", "batch.session_date", "Session date must be a real ISO calendar date")
        )

    participants = batch.get("participants")
    if isinstance(participants, list):
        ids = [item.get("participant_id") for item in participants if isinstance(item, dict)]
        if len(ids) != len(set(ids)):
            result.errors.append(
                GateMessage("playtest.participant_duplicate", "batch.participants", "Anonymous participant IDs must be unique")
            )
        for index, participant in enumerate(participants):
            if not isinstance(participant, dict):
                continue
            trace = participant.get("trace_summary")
            interview = participant.get("interview")
            if not isinstance(trace, dict) or not isinstance(interview, dict):
                continue
            found = trace.get("chapter1_critical_anchors_found")
            total = trace.get("chapter1_critical_anchors_total")
            if isinstance(found, int) and isinstance(total, int) and total > 0 and found > total:
                result.errors.append(
                    GateMessage("playtest.anchor_count", f"batch.participants[{index}].trace_summary", "Found anchors cannot exceed total anchors")
                )
            completed = trace.get("completed_first_run")
            ending_id = trace.get("ending_id")
            if completed is True and not isinstance(ending_id, str):
                result.errors.append(
                    GateMessage("playtest.ending", f"batch.participants[{index}].trace_summary.ending_id", "Completed runs require an ending ID")
                )
            if completed is False and ending_id is not None:
                result.errors.append(
                    GateMessage("playtest.ending", f"batch.participants[{index}].trace_summary.ending_id", "Incomplete runs must not claim an ending")
                )
            if interview.get("wants_replay_after_path_review") is True and trace.get("path_review_opened") is not True:
                result.errors.append(
                    GateMessage("playtest.replay_basis", f"batch.participants[{index}]", "Replay intent requires the path review to have been opened")
                )

    if result.errors:
        result.evidence = {"evaluation_complete": False, "participant_count": len(participants) if isinstance(participants, list) else 0}
        return result.finish()

    assert isinstance(participants, list)
    metric_results = [evaluate_metric(spec, participants) for spec in metrics]
    for metric in metric_results:
        if not metric["passed"]:
            result.errors.append(
                GateMessage(
                    "playtest.metric_threshold",
                    f"metrics.{metric['field']}",
                    f"Observed {metric['value']} did not satisfy {metric['comparison']} {metric['threshold']}",
                )
            )
    result.evidence = {
        "evaluation_complete": True,
        "batch_id": batch["batch_id"],
        "batch_digest": canonical_digest(batch),
        "participant_count": len(participants),
        "metrics": metric_results,
        "participant_trace_digests": {
            item["participant_id"]: canonical_digest(item["trace_summary"]) for item in participants
        },
        "participant_record_digests": {
            item["participant_id"]: canonical_digest(item) for item in participants
        },
        "privacy": {"anonymous_ids": True, "consent_required": True, "collection_mode": "local_manual"},
    }
    return result.finish()


def evaluate_metric(spec: dict[str, Any], participants: list[dict[str, Any]]) -> dict[str, Any]:
    field = spec.get("field")
    comparison = spec.get("comparison")
    threshold = spec.get("threshold")
    values = [participant_metric_value(item, field) for item in participants]
    if comparison == "ratio_gte":
        value = sum(1 for item in values if item is True) / len(values)
        passed = value >= threshold
    elif comparison == "qualified_ratio_gte":
        floor = spec.get("participant_floor")
        value = sum(1 for item in values if isinstance(item, (int, float)) and item >= floor) / len(values)
        passed = value >= threshold
    elif comparison == "count_eq":
        value = sum(1 for item in values if item is True)
        passed = value == threshold
    else:
        raise G6ConfigError(f"Unsupported experience metric comparison: {comparison}")
    output = {
        "field": field,
        "comparison": comparison,
        "value": round(value, 3) if isinstance(value, float) else value,
        "threshold": threshold,
        "passed": passed,
    }
    if "participant_floor" in spec:
        output["participant_floor"] = spec["participant_floor"]
    return output


def participant_metric_value(participant: dict[str, Any], field: str) -> Any:
    trace = participant["trace_summary"]
    interview = participant["interview"]
    if field == "completed_first_run":
        return trace[field]
    if field == "chapter1_key_anchor_found_ratio":
        return trace["chapter1_critical_anchors_found"] / trace["chapter1_critical_anchors_total"]
    if field == "blocked_by_hidden_key_anchor":
        return trace[field]
    if field in interview:
        return interview[field]
    raise G6ConfigError(f"Unsupported experience metric field: {field}")


def apply_g6_outcome(
    pack_dir: str | Path,
    batch_path: str | Path,
    report_path: str | Path,
    *,
    attribution_receipt: str | Path | None = None,
    loop_manifest_path: str | Path | None = None,
    dependent_pack_manifests: Iterable[str | Path] | None = None,
) -> dict[str, Any]:
    current = run_g6(pack_dir, batch_path).to_dict()
    stored = load_object(report_path, "G6 report")
    if canonical_digest(stored) != canonical_digest(current):
        raise G6ConfigError("Stale G6 report: report does not match the current pack, batch, and metrics")
    schema_errors = validate_kernel_document("gate-result.schema.json", stored)
    if schema_errors:
        raise G6ConfigError("Invalid G6 GateResult: " + "; ".join(schema_errors))
    if stored.get("evidence", {}).get("evaluation_complete") is not True:
        raise G6ConfigError("Invalid player data cannot be applied as a G6 tier decision")

    context = load_content_pack(pack_dir)
    batch = load_object(batch_path, "playtest batch")
    loop_path = Path(loop_manifest_path) if loop_manifest_path else context.loop_root / "loop.json"
    loop = load_object(loop_path, "loop manifest")
    failed = stored.get("status") == "failed"
    receipt: dict[str, Any] | None = None
    if failed:
        if attribution_receipt is None:
            raise G6ConfigError("A failed G6 batch requires a playtest attribution DecisionReceipt")
        receipt = validate_decision_receipt(
            attribution_receipt,
            checkpoint="playtest_attribution",
            subject_path=report_path,
            allowed_decisions={"content_issue", "loop_issue", "inconclusive"},
        )
    elif stored.get("status") != "passed":
        raise G6ConfigError(f"G6 status cannot be applied: {stored.get('status')}")

    evidence = {
        "batch_id": batch["batch_id"],
        "digest": canonical_digest(stored),
        "result": "failed" if failed else "passed",
    }
    if receipt is not None:
        evidence["attribution"] = receipt["decision"]
        evidence["attribution_digest"] = artifact_digest(attribution_receipt)
    next_loop = deepcopy(loop)
    next_loop["tier"] = "experimental" if failed else "verified"
    next_loop["verification"]["status"] = "experimental" if failed else "verified"
    append_evidence(next_loop["verification"]["evidence"], evidence)
    loop_schema = load_object(ROOT / "loop_packages" / "loop-package.schema.json", "loop package schema")
    loop_errors = sorted(Draft202012Validator(loop_schema).iter_errors(next_loop), key=lambda item: list(item.absolute_path))
    if loop_errors:
        raise G6ConfigError("G6 would create an invalid loop manifest: " + "; ".join(item.message for item in loop_errors))

    targets = list(dependent_pack_manifests) if dependent_pack_manifests is not None else discover_dependent_manifests(context)
    next_manifests: list[tuple[Path, dict[str, Any]]] = []
    for target in targets:
        path = Path(target)
        manifest = load_object(path, "dependent pack manifest")
        ref = manifest.get("loop_package", {})
        if ref.get("id") != loop.get("id") or ref.get("version") != loop.get("version"):
            continue
        updated = deepcopy(manifest)
        updated["loop_package"]["tier"] = next_loop["tier"]
        updated["loop_package"]["verification_status"] = next_loop["verification"]["status"]
        updated["experimental_notice"] = failed
        errors = validate_kernel_document("pack.schema.json", updated)
        if errors:
            raise G6ConfigError(f"G6 would create an invalid pack manifest at {path}: " + "; ".join(errors))
        next_manifests.append((path, updated))

    write_object(loop_path, next_loop)
    for path, manifest in next_manifests:
        write_object(path, manifest)
    return {
        "schema_version": "narrative_g6_application_v1",
        "status": "experimental" if failed else "verified",
        "evidence_digest": evidence["digest"],
        "updated_loop_manifest": str(loop_path),
        "updated_pack_count": len(next_manifests),
    }


def discover_dependent_manifests(context: Any) -> list[Path]:
    candidates = list((ROOT / "content_packs").glob("*/v*/pack.json"))
    own = context.root / "pack.json"
    if own not in candidates:
        candidates.append(own)
    return sorted(set(path.resolve() for path in candidates))


def append_evidence(items: list[dict[str, Any]], evidence: dict[str, Any]) -> None:
    for existing in items:
        if existing.get("batch_id") == evidence["batch_id"]:
            if existing != evidence:
                raise G6ConfigError("Batch ID already exists with different G6 evidence")
            return
    items.append(evidence)


def load_object(path: str | Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise G6ConfigError(f"Missing {label}: {path}") from exc
    except json.JSONDecodeError as exc:
        raise G6ConfigError(f"Invalid {label} JSON: {exc.msg}") from exc
    if not isinstance(value, dict):
        raise G6ConfigError(f"{label} must be a JSON object")
    return value


def write_object(path: str | Path, value: dict[str, Any]) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
