from __future__ import annotations

import json
from collections import deque
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable

from .content_pack import ContentPackContext, ContentPackLoadError, load_content_pack, resolve_relative_file
from .kernel_contract import ROOT, canonical_digest, file_digest, validate_kernel_document


GATE_VERSION = "1.0.0"
GATE_IDS = ("G1", "G2", "G3", "G4", "G5", "G6")


@dataclass(frozen=True)
class GateMessage:
    code: str
    location: str
    message: str

    def to_dict(self) -> dict[str, str]:
        return {"code": self.code, "location": self.location, "message": self.message}


@dataclass
class GateResult:
    gate_id: str
    input_digest: str
    status: str = "passed"
    errors: list[GateMessage] = field(default_factory=list)
    warnings: list[GateMessage] = field(default_factory=list)
    evidence: dict[str, Any] = field(default_factory=dict)

    def finish(self) -> "GateResult":
        if self.errors:
            self.status = "failed"
        return self

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "narrative_gate_result_v1",
            "gate_id": self.gate_id,
            "gate_version": GATE_VERSION,
            "status": self.status,
            "input_digest": self.input_digest,
            "errors": [message.to_dict() for message in self.errors],
            "warnings": [message.to_dict() for message in self.warnings],
            "evidence": self.evidence,
        }


def run_pack_gates(
    pack_dir: str | Path,
    through: str = "G4",
    g5_runner: Callable[[ContentPackContext, str], GateResult] | None = None,
) -> list[GateResult]:
    if through not in GATE_IDS:
        raise ValueError(f"Unknown gate id: {through}")
    try:
        context = load_content_pack(pack_dir)
        digest = pack_input_digest(context)
    except ContentPackLoadError as exc:
        digest = canonical_digest({"pack_dir": str(Path(pack_dir).resolve())})
        result = GateResult("G1", digest)
        result.errors.append(GateMessage("pack.load", "pack", str(exc)))
        return [result.finish()]

    runners: list[tuple[str, Callable[[ContentPackContext, str], GateResult]]] = [
        ("G1", run_g1),
        ("G2", run_g2),
        ("G3", run_g3),
        ("G4", run_g4),
    ]
    results: list[GateResult] = []
    target_index = GATE_IDS.index(through)
    for gate_id, runner in runners:
        if GATE_IDS.index(gate_id) > target_index:
            break
        result = runner(context, digest)
        results.append(result)
        if result.status == "failed":
            return results
    if target_index >= GATE_IDS.index("G5"):
        if g5_runner is None:
            pending = GateResult("G5", digest, status="pending")
            pending.warnings.append(
                GateMessage("g5.not_configured", "runtime", "G5 browser runner is not configured")
            )
            results.append(pending)
        else:
            results.append(g5_runner(context, digest))
    return results


def pack_input_digest(context: ContentPackContext) -> str:
    return canonical_digest(
        {
            "pack": context.manifest,
            "game": context.game,
            "state_registry": context.state_registry,
            "provenance": context.provenance,
            "loop": context.loop_manifest,
            "loop_schema": context.loop_schema_extension,
            "loop_rules": context.loop_acceptance_rules,
            "loop_metrics": context.loop_experience_metrics,
        }
    )


def run_g1(context: ContentPackContext, digest: str) -> GateResult:
    result = GateResult("G1", digest)
    documents = (
        ("pack.json", "pack.schema.json", context.manifest),
        ("game.json", "progression.schema.json", context.game),
        ("state_registry.json", "state.schema.json", context.state_registry),
        ("provenance", "provenance.schema.json", context.provenance),
    )
    for location, schema_name, document in documents:
        for error in validate_kernel_document(schema_name, document):
            result.errors.append(GateMessage("schema.invalid", location, error))

    result.errors.extend(validate_loop_manifest(context))
    result.errors.extend(validate_loop_extension(context))
    result.errors.extend(validate_provenance_integrity(context))

    pack_loop = context.manifest.get("loop_package", {})
    loop = context.loop_manifest
    for field in ("id", "version", "tier"):
        if pack_loop.get(field) != loop.get(field):
            result.errors.append(
                GateMessage("loop.mismatch", f"pack.loop_package.{field}", "Content pack and installed loop package differ")
            )
    if pack_loop.get("verification_status") != loop.get("verification", {}).get("status"):
        result.errors.append(
            GateMessage(
                "loop.verification_mismatch",
                "pack.loop_package.verification_status",
                "Content pack verification status must match the installed loop package",
            )
        )
    if context.manifest.get("authorship") != context.provenance.get("authorship"):
        result.errors.append(
            GateMessage("provenance.authorship", "provenance.authorship", "Authorship must match pack.json")
        )

    declared_surfaces = set(context.manifest.get("surfaces_used", []))
    actual_surfaces = {surface.get("type") for _, surface, _, _ in iter_surfaces(context.game)}
    if declared_surfaces != actual_surfaces:
        result.errors.append(
            GateMessage(
                "surface.declaration",
                "pack.surfaces_used",
                f"Declared surfaces {sorted(declared_surfaces)} do not match actual {sorted(actual_surfaces)}",
            )
        )
    result.evidence = {
        "schemas": [schema for _, schema, _ in documents],
        "loop_package": f"{loop.get('id')}@{loop.get('version')}",
        "surfaces_used": sorted(item for item in actual_surfaces if isinstance(item, str)),
    }
    return result.finish()


def validate_loop_manifest(context: ContentPackContext) -> list[GateMessage]:
    schema_path = ROOT / "loop_packages" / "loop-package.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    try:
        from jsonschema import Draft202012Validator
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("Python package 'jsonschema' is required") from exc
    validator = Draft202012Validator(schema)
    messages: list[GateMessage] = []
    for error in sorted(validator.iter_errors(context.loop_manifest), key=lambda item: list(item.absolute_path)):
        location = ".".join(str(part) for part in error.absolute_path) or "<root>"
        messages.append(GateMessage("loop.schema", f"loop.{location}", error.message))
    for name, relative in context.loop_manifest.get("entrypoints", {}).items():
        try:
            resolve_relative_file(context.loop_root, relative, f"loop.entrypoints.{name}")
        except ContentPackLoadError as exc:
            messages.append(GateMessage("loop.entrypoint", f"loop.entrypoints.{name}", str(exc)))
    return messages


def validate_loop_extension(context: ContentPackContext) -> list[GateMessage]:
    try:
        from jsonschema import Draft202012Validator
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("Python package 'jsonschema' is required") from exc
    validator = Draft202012Validator(context.loop_schema_extension)
    messages: list[GateMessage] = []
    for error in sorted(validator.iter_errors(context.game), key=lambda item: list(item.absolute_path)):
        location = ".".join(str(part) for part in error.absolute_path) or "<root>"
        messages.append(GateMessage("loop.extension", f"game.{location}", error.message))
    return messages


def validate_provenance_integrity(context: ContentPackContext) -> list[GateMessage]:
    messages: list[GateMessage] = []
    for index, artifact in enumerate(context.provenance.get("artifacts", [])):
        location = f"provenance.artifacts[{index}]"
        try:
            path = resolve_relative_file(context.root, artifact.get("path"), f"{location}.path")
        except ContentPackLoadError as exc:
            messages.append(GateMessage("provenance.path", location, str(exc)))
            continue
        if file_digest(path) != artifact.get("sha256"):
            messages.append(GateMessage("provenance.checksum", location, "Artifact checksum does not match"))
    return messages


def run_g2(context: ContentPackContext, digest: str) -> GateResult:
    result = GateResult("G2", digest)
    game = context.game
    scene_ids = collect_unique_ids(game.get("scenes", []), "scene", result)
    ending_ids = collect_unique_ids(game.get("endings", []), "ending", result)
    if game.get("entry_scene_id") not in scene_ids:
        result.errors.append(GateMessage("progression.entry", "game.entry_scene_id", "Entry scene does not exist"))
    if scene_ids & ending_ids:
        result.errors.append(GateMessage("id.collision", "game", "Scene and ending ids must be disjoint"))

    state_definitions = validate_state_registry(context, result)
    state_reads: dict[str, list[str]] = {}
    state_writes: dict[str, list[tuple[str, str, Any]]] = {}
    action_ids: set[str] = set()
    anchor_ids: set[str] = set()
    surface_ids: set[str] = set()
    fragment_ids: set[str] = set()
    ending_targets: set[str] = set()
    graph_edges: dict[str, set[str]] = {scene_id: set() for scene_id in scene_ids}

    loop_id = context.manifest.get("loop_package", {}).get("id")
    validate_extension_namespaces(game, loop_id, result)
    for scene_index, scene in enumerate(game.get("scenes", [])):
        scene_id = scene.get("id", f"scenes[{scene_index}]")
        for echo_index, echo in enumerate(scene.get("echoes", [])):
            collect_condition_reads(echo.get("requirements", []), f"{scene_id}.echoes[{echo_index}]", state_reads)
        scene_action_ids: set[str] = set()
        actions_by_id: dict[str, dict[str, Any]] = {}
        for action_index, action in enumerate(scene.get("actions", [])):
            location = f"{scene_id}.actions[{action_index}]"
            action_id = action.get("id")
            register_id(action_id, action_ids, "action", location, result)
            if isinstance(action_id, str):
                scene_action_ids.add(action_id)
                actions_by_id[action_id] = action
            collect_condition_reads(action.get("requirements", []), location, state_reads)
            collect_effect_writes(action.get("effects", []), location, state_writes)
            target = action.get("target", {})
            target_id = target.get("id")
            target_type = target.get("type")
            if target_type == "scene":
                if target_id not in scene_ids:
                    result.errors.append(GateMessage("target.missing", f"{location}.target", "Scene target does not exist"))
                elif isinstance(scene_id, str):
                    graph_edges.setdefault(scene_id, set()).add(target_id)
            elif target_type == "ending":
                if target_id not in ending_ids:
                    result.errors.append(GateMessage("target.missing", f"{location}.target", "Ending target does not exist"))
                else:
                    ending_targets.add(target_id)

        for _, surface, depth, parent_anchor_ids in iter_surfaces_from_scene(scene):
            surface_location = f"{scene_id}.{surface.get('id', '<surface>')}"
            register_id(surface.get("id"), surface_ids, "surface", surface_location, result)
            validate_surface(context, surface, surface_location, result)
            for anchor, anchor_depth, ancestor_ids in iter_anchors(surface, depth, parent_anchor_ids):
                anchor_location = f"{scene_id}.{anchor.get('id', '<anchor>')}"
                register_id(anchor.get("id"), anchor_ids, "anchor", anchor_location, result)
                fragment = anchor.get("fragment", {})
                register_id(fragment.get("id"), fragment_ids, "fragment", f"{anchor_location}.fragment", result)
                collect_effect_writes(anchor.get("effects", []), anchor_location, state_writes)
                for unlocked_id in anchor.get("unlocks_actions", []):
                    if unlocked_id not in scene_action_ids:
                        result.errors.append(
                            GateMessage("unlock.missing", f"{anchor_location}.unlocks_actions", "Unlocked action must exist in the same scene")
                        )
                        continue
                    action = actions_by_id[unlocked_id]
                    if anchor.get("discoverability") == "hidden_optional" and action.get("consequence_level") != "local":
                        result.errors.append(
                            GateMessage(
                                "fairness.hidden_optional",
                                anchor_location,
                                "hidden_optional anchor cannot unlock chapter/global/ending action",
                            )
                        )

    for echo_index, echo in enumerate(game.get("profile_echoes", [])):
        collect_condition_reads(echo.get("requirements", []), f"profile_echoes[{echo_index}]", state_reads)
    validate_state_usage(state_definitions, state_reads, state_writes, result)

    reachable_scenes = graph_reachable(game.get("entry_scene_id"), graph_edges)
    for scene_id in sorted(scene_ids - reachable_scenes):
        result.errors.append(GateMessage("progression.unreachable_scene", scene_id, "Scene is not structurally reachable"))
    for ending_id in sorted(ending_ids - ending_targets):
        result.errors.append(GateMessage("progression.unreachable_ending", ending_id, "Ending is not targeted by any action"))

    result.evidence = {
        "scenes": len(scene_ids),
        "endings": len(ending_ids),
        "actions": len(action_ids),
        "anchors": len(anchor_ids),
        "registered_states": len(state_definitions),
    }
    return result.finish()


def validate_state_registry(context: ContentPackContext, result: GateResult) -> dict[str, dict[str, Any]]:
    definitions: dict[str, dict[str, Any]] = {}
    for index, state in enumerate(context.state_registry.get("states", [])):
        key = state.get("key")
        location = f"state_registry.states[{index}]"
        if key in definitions:
            result.errors.append(GateMessage("state.duplicate", location, f"Duplicate state key: {key}"))
            continue
        if isinstance(key, str):
            definitions[key] = state
        expected = state.get("type")
        if not value_matches_type(state.get("initial"), expected):
            result.errors.append(GateMessage("state.initial_type", f"{location}.initial", f"Initial value does not match {expected}"))
    return definitions


def validate_state_usage(
    definitions: dict[str, dict[str, Any]],
    reads: dict[str, list[str]],
    writes: dict[str, list[tuple[str, str, Any]]],
    result: GateResult,
) -> None:
    used = set(reads) | set(writes)
    for state in sorted(used - set(definitions)):
        result.errors.append(GateMessage("state.unregistered", state, "State is used but not registered"))
    for state in sorted(set(definitions) - set(reads)):
        result.errors.append(GateMessage("state.dead", state, "Registered state is never read"))
    for state in sorted(set(definitions) - set(writes)):
        result.errors.append(GateMessage("state.unwritten", state, "Registered state is never written"))

    for state, locations in reads.items():
        definition = definitions.get(state)
        if not definition:
            continue
        for location, requirement in locations:
            if "equals" in requirement and not value_matches_type(requirement["equals"], definition.get("type")):
                result.errors.append(GateMessage("state.condition_type", location, "equals value type does not match state"))
            if ("min" in requirement or "max" in requirement) and definition.get("type") != "number":
                result.errors.append(GateMessage("state.condition_type", location, "min/max requires a numeric state"))
    for state, entries in writes.items():
        definition = definitions.get(state)
        if not definition:
            continue
        for location, operation, value in entries:
            if operation == "add" and (definition.get("type") != "number" or not is_number(value)):
                result.errors.append(GateMessage("state.effect_type", location, "add requires numeric state and value"))
            if operation == "set" and not value_matches_type(value, definition.get("type")):
                result.errors.append(GateMessage("state.effect_type", location, "set value type does not match state"))


def validate_surface(
    context: ContentPackContext,
    surface: dict[str, Any],
    location: str,
    result: GateResult,
) -> None:
    surface_type = surface.get("type")
    content = surface.get("content", {})
    for anchor in surface.get("anchors", []):
        locator = anchor.get("locator", {})
        expected_kind = {"text": "text", "image": "region", "html": "selector"}.get(surface_type)
        if locator.get("kind") != expected_kind:
            result.errors.append(
                GateMessage("surface.locator_type", f"{location}.{anchor.get('id', '<anchor>')}.locator", f"{surface_type} surface requires {expected_kind} locator")
            )
        if surface_type == "text" and locator.get("kind") == "text":
            text = content.get("text", "")
            exact = locator.get("exact", "")
            occurrence = locator.get("occurrence", 1)
            if not exact or text.count(exact) < occurrence:
                result.errors.append(GateMessage("surface.text_span", location, "Text locator occurrence does not exist"))
        if surface_type == "image" and locator.get("shape") == "rect":
            if float(locator.get("x", 0)) + float(locator.get("width", 0)) > 1 or float(locator.get("y", 0)) + float(locator.get("height", 0)) > 1:
                result.errors.append(GateMessage("surface.region_bounds", location, "Image rectangle exceeds normalized bounds"))
    if surface_type in {"image", "html"}:
        asset = content.get("asset")
        try:
            resolve_relative_file(context.root, asset, f"{location}.content.asset")
        except ContentPackLoadError as exc:
            result.errors.append(GateMessage("surface.asset", location, str(exc)))


def validate_extension_namespaces(value: Any, loop_id: Any, result: GateResult, path: str = "game") -> None:
    if isinstance(value, dict):
        extensions = value.get("extensions")
        if isinstance(extensions, dict):
            unexpected = set(extensions) - ({loop_id} if isinstance(loop_id, str) else set())
            for key in sorted(unexpected):
                result.errors.append(
                    GateMessage("extension.foreign_namespace", f"{path}.extensions.{key}", "Only the declared loop package namespace is allowed")
                )
        for key, child in value.items():
            validate_extension_namespaces(child, loop_id, result, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            validate_extension_namespaces(child, loop_id, result, f"{path}[{index}]")


def run_g3(context: ContentPackContext, digest: str) -> GateResult:
    result = GateResult("G3", digest)
    rules = context.loop_acceptance_rules
    structure = rules.get("structure", {})
    game = context.game
    chapter_ids = {
        chapter.get("id")
        for chapter in game.get("extensions", {}).get("investigation", {}).get("chapters", [])
    }
    initial_state = {
        state["key"]: state["initial"] for state in context.state_registry.get("states", []) if "key" in state
    }
    for scene in game.get("scenes", []):
        scene_id = scene.get("id", "<scene>")
        metadata = scene.get("extensions", {}).get("investigation", {})
        if metadata.get("chapter_id") not in chapter_ids:
            result.errors.append(GateMessage("investigation.chapter", scene_id, "Scene references an undeclared chapter"))
        if not metadata.get("main_scene", True):
            continue
        actions = scene.get("actions", [])
        minimum = structure.get("min_actions_per_main_scene", 2)
        maximum = structure.get("max_actions_per_main_scene", 4)
        if not minimum <= len(actions) <= maximum:
            result.errors.append(
                GateMessage("investigation.action_budget", scene_id, f"Main scene must contain {minimum}–{maximum} actions")
            )
        anchors = list(iter_scene_anchors_with_effect_path(scene))
        obvious = sum(1 for anchor, _, _, _ in anchors if anchor.get("discoverability") == "obvious")
        if obvious < structure.get("min_obvious_anchors_per_main_scene", 1):
            result.errors.append(GateMessage("investigation.obvious_anchor", scene_id, "Main scene needs an obvious anchor"))
        max_depth = max((depth for _, depth, _, _ in anchors), default=0)
        if max_depth > structure.get("max_anchor_depth", 3):
            result.errors.append(GateMessage("investigation.depth", scene_id, "Anchor nesting exceeds loop limit"))

        action_by_id = {action.get("id"): action for action in actions}
        unlocked: set[str] = set()
        for anchor, _, path_effects, location in anchors:
            for action_id in anchor.get("unlocks_actions", []):
                unlocked.add(action_id)
                action = action_by_id.get(action_id)
                if not action:
                    continue
                projected = apply_effects(deepcopy(initial_state), path_effects)
                if not action.get("requirements"):
                    result.errors.append(
                        GateMessage("investigation.unlock_contract", location, "Observe-unlocked action must have a state requirement")
                    )
                elif not all(state_matches(projected, requirement) for requirement in action.get("requirements", [])):
                    result.errors.append(
                        GateMessage("investigation.unlock_contract", location, f"Anchor effects do not satisfy action {action_id}")
                    )
        if not (unlocked & set(action_by_id)):
            result.errors.append(
                GateMessage("investigation.observe_action", scene_id, "Main scene needs an anchor-unlocked current-scene action")
            )

    if len(game.get("endings", [])) < structure.get("min_endings", 3):
        result.errors.append(GateMessage("investigation.endings", "game.endings", "Investigation loop requires three endings"))
    entry_scene = next((scene for scene in game.get("scenes", []) if scene.get("id") == game.get("entry_scene_id")), None)
    if entry_scene:
        entry_anchors = [item[0] for item in iter_scene_anchors_with_effect_path(entry_scene)]
        if not any(anchor.get("guidance") for anchor in entry_anchors):
            result.errors.append(GateMessage("investigation.guidance", entry_scene["id"], "Entry scene needs first-observe guidance"))
        if not any(anchor.get("unlock_guidance") for anchor in entry_anchors if anchor.get("unlocks_actions")):
            result.errors.append(GateMessage("investigation.unlock_guidance", entry_scene["id"], "Entry scene needs first-unlock guidance"))
    result.evidence = {
        "loop": "investigation@1.0.0",
        "main_scenes": sum(
            1 for scene in game.get("scenes", []) if scene.get("extensions", {}).get("investigation", {}).get("main_scene", True)
        ),
        "endings": len(game.get("endings", [])),
    }
    return result.finish()


def run_g4(context: ContentPackContext, digest: str) -> GateResult:
    result = GateResult("G4", digest)
    game = context.game
    scene_by_id = {scene["id"]: scene for scene in game.get("scenes", [])}
    ending_ids = {ending["id"] for ending in game.get("endings", [])}
    initial_state = {
        state["key"]: state["initial"] for state in context.state_registry.get("states", [])
    }
    state_limit = int(context.loop_acceptance_rules.get("simulation", {}).get("state_limit", 100000))
    queue = deque(
        [
            (
                game.get("entry_scene_id"),
                initial_state,
                frozenset(),
                frozenset(),
                [],
            )
        ]
    )
    seen: set[tuple[Any, ...]] = set()
    reachable_scenes: set[str] = set()
    witnesses: dict[str, list[dict[str, str]]] = {}
    proof_complete = False

    while queue and len(seen) < state_limit:
        scene_id, state, opened, chosen, path = queue.popleft()
        key = (scene_id, normalize_state(state), tuple(sorted(opened)), tuple(sorted(chosen)))
        if key in seen or scene_id not in scene_by_id:
            continue
        seen.add(key)
        reachable_scenes.add(scene_id)
        scene = scene_by_id[scene_id]

        for anchor, _, ancestors, _ in iter_scene_anchors_with_ancestors(scene):
            anchor_id = anchor["id"]
            if anchor_id in opened or not set(ancestors) <= set(opened):
                continue
            next_state = apply_effects(deepcopy(state), anchor.get("effects", []))
            queue.append(
                (
                    scene_id,
                    next_state,
                    opened | {anchor_id},
                    chosen,
                    [*path, {"kind": "anchor", "id": anchor_id}],
                )
            )

        for action in scene.get("actions", []):
            action_id = action["id"]
            if action_id in chosen or not all(state_matches(state, req) for req in action.get("requirements", [])):
                continue
            next_state = apply_effects(deepcopy(state), action.get("effects", []))
            next_path = [*path, {"kind": "action", "id": action_id}]
            target = action["target"]
            if target["type"] == "ending":
                witnesses.setdefault(target["id"], next_path)
            else:
                queue.append((target["id"], next_state, opened, chosen | {action_id}, next_path))

        # G4 is an existential reachability proof, not an exhaustive enumeration of
        # every optional-observation subset. Once every scene and ending has a
        # replayable witness, continuing would add no evidence and can explode
        # combinatorially for investigation scenes with many independent anchors.
        proof_complete = reachable_scenes == set(scene_by_id) and set(witnesses) == ending_ids
        if proof_complete:
            break

    if queue and not proof_complete:
        result.errors.append(GateMessage("simulation.limit", "G4", f"State exploration exceeded {state_limit} states"))
    missing_scenes = set(scene_by_id) - reachable_scenes
    missing_endings = ending_ids - set(witnesses)
    for scene_id in sorted(missing_scenes):
        result.errors.append(GateMessage("simulation.unreachable_scene", scene_id, "No executable path reaches scene"))
    for ending_id in sorted(missing_endings):
        result.errors.append(GateMessage("simulation.unreachable_ending", ending_id, "No executable path reaches ending"))
    result.evidence = {
        "visited_state_count": len(seen),
        "reachable_scenes": sorted(reachable_scenes),
        "ending_witnesses": {key: witnesses[key] for key in sorted(witnesses)},
    }
    return result.finish()


def collect_unique_ids(items: list[dict[str, Any]], kind: str, result: GateResult) -> set[str]:
    output: set[str] = set()
    for index, item in enumerate(items):
        register_id(item.get("id"), output, kind, f"{kind}[{index}]", result)
    return output


def register_id(value: Any, output: set[str], kind: str, location: str, result: GateResult) -> None:
    if not isinstance(value, str) or not value:
        return
    if value in output:
        result.errors.append(GateMessage(f"id.duplicate_{kind}", location, f"Duplicate {kind} id: {value}"))
    output.add(value)


def iter_surfaces(game: dict[str, Any]) -> Iterable[tuple[str, dict[str, Any], int, tuple[str, ...]]]:
    for scene in game.get("scenes", []):
        for _, surface, depth, parents in iter_surfaces_from_scene(scene):
            yield scene.get("id", "<scene>"), surface, depth, parents


def iter_surfaces_from_scene(scene: dict[str, Any]) -> Iterable[tuple[str, dict[str, Any], int, tuple[str, ...]]]:
    scene_id = scene.get("id", "<scene>")
    for surface in scene.get("surfaces", []):
        yield from walk_surface(scene_id, surface, 1, ())


def walk_surface(
    scene_id: str,
    surface: dict[str, Any],
    depth: int,
    parent_anchor_ids: tuple[str, ...],
) -> Iterable[tuple[str, dict[str, Any], int, tuple[str, ...]]]:
    yield scene_id, surface, depth, parent_anchor_ids
    for anchor in surface.get("anchors", []):
        next_parents = (*parent_anchor_ids, anchor.get("id", "<anchor>"))
        for child_surface in anchor.get("fragment", {}).get("surfaces", []):
            yield from walk_surface(scene_id, child_surface, depth + 1, next_parents)


def iter_anchors(
    surface: dict[str, Any],
    depth: int = 1,
    parent_anchor_ids: tuple[str, ...] = (),
) -> Iterable[tuple[dict[str, Any], int, tuple[str, ...]]]:
    for anchor in surface.get("anchors", []):
        yield anchor, depth, parent_anchor_ids


def iter_scene_anchors_with_effect_path(
    scene: dict[str, Any],
) -> Iterable[tuple[dict[str, Any], int, list[dict[str, Any]], str]]:
    for surface in scene.get("surfaces", []):
        yield from walk_anchors_with_effect_path(surface, 1, [], scene.get("id", "<scene>"))


def walk_anchors_with_effect_path(
    surface: dict[str, Any],
    depth: int,
    inherited_effects: list[dict[str, Any]],
    scene_id: str,
) -> Iterable[tuple[dict[str, Any], int, list[dict[str, Any]], str]]:
    for anchor in surface.get("anchors", []):
        path_effects = [*inherited_effects, *anchor.get("effects", [])]
        location = f"{scene_id}.{anchor.get('id', '<anchor>')}"
        yield anchor, depth, path_effects, location
        for child_surface in anchor.get("fragment", {}).get("surfaces", []):
            yield from walk_anchors_with_effect_path(child_surface, depth + 1, path_effects, scene_id)


def iter_scene_anchors_with_ancestors(
    scene: dict[str, Any],
) -> Iterable[tuple[dict[str, Any], int, tuple[str, ...], str]]:
    for surface in scene.get("surfaces", []):
        yield from walk_anchors_with_ancestors(surface, 1, (), scene.get("id", "<scene>"))


def walk_anchors_with_ancestors(
    surface: dict[str, Any],
    depth: int,
    ancestors: tuple[str, ...],
    scene_id: str,
) -> Iterable[tuple[dict[str, Any], int, tuple[str, ...], str]]:
    for anchor in surface.get("anchors", []):
        location = f"{scene_id}.{anchor.get('id', '<anchor>')}"
        yield anchor, depth, ancestors, location
        next_ancestors = (*ancestors, anchor.get("id", "<anchor>"))
        for child_surface in anchor.get("fragment", {}).get("surfaces", []):
            yield from walk_anchors_with_ancestors(child_surface, depth + 1, next_ancestors, scene_id)


def collect_condition_reads(
    requirements: list[dict[str, Any]],
    location: str,
    output: dict[str, list[tuple[str, dict[str, Any]]]],
) -> None:
    for index, requirement in enumerate(requirements):
        state = requirement.get("state")
        if isinstance(state, str):
            output.setdefault(state, []).append((f"{location}.requirements[{index}]", requirement))


def collect_effect_writes(
    effects: list[dict[str, Any]],
    location: str,
    output: dict[str, list[tuple[str, str, Any]]],
) -> None:
    for index, effect in enumerate(effects):
        for operation in ("set", "add"):
            for state, value in effect.get(operation, {}).items():
                output.setdefault(state, []).append((f"{location}.effects[{index}].{operation}.{state}", operation, value))


def graph_reachable(entry: Any, edges: dict[str, set[str]]) -> set[str]:
    pending = [entry]
    seen: set[str] = set()
    while pending:
        node = pending.pop()
        if not isinstance(node, str) or node in seen or node not in edges:
            continue
        seen.add(node)
        pending.extend(edges[node] - seen)
    return seen


def apply_effects(state: dict[str, Any], effects: list[dict[str, Any]]) -> dict[str, Any]:
    for effect in effects:
        for key, value in effect.get("set", {}).items():
            state[key] = value
        for key, value in effect.get("add", {}).items():
            state[key] = to_number(state.get(key, 0)) + to_number(value)
    return state


def state_matches(state: dict[str, Any], requirement: dict[str, Any]) -> bool:
    current = state.get(requirement.get("state"))
    if "equals" in requirement:
        return current == requirement["equals"]
    if "min" in requirement:
        return to_number(current) >= to_number(requirement["min"])
    if "max" in requirement:
        return to_number(current) <= to_number(requirement["max"])
    return False


def normalize_state(state: dict[str, Any]) -> tuple[tuple[str, Any], ...]:
    return tuple(sorted(state.items()))


def to_number(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def value_matches_type(value: Any, expected: Any) -> bool:
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "number":
        return is_number(value)
    if expected == "string":
        return isinstance(value, str)
    return False
