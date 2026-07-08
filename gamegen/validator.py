from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class ValidationMessage:
    level: str
    location: str
    message: str


def load_game(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def validate_game(game: dict[str, Any]) -> list[ValidationMessage]:
    messages: list[ValidationMessage] = []
    scenes = game.get("scenes", [])
    endings = game.get("endings", [])
    if not isinstance(scenes, list) or not scenes:
        return [ValidationMessage("error", "game.scenes", "Game must contain scenes")]

    scene_ids = {scene.get("id") for scene in scenes}
    ending_ids = {ending.get("id") for ending in endings if isinstance(ending, dict)}
    choice_ids: set[str] = set()
    observe_ids: set[str] = set()
    guidance_ids: set[str] = set()
    state_writes: set[str] = set()
    state_reads: set[str] = set()
    observe_unlocked_choices_by_scene: dict[str, set[str]] = {}

    start_scene_id = game.get("start_scene_id")
    if start_scene_id not in scene_ids:
        messages.append(ValidationMessage("error", "game.start_scene_id", "Start scene does not exist"))

    for scene in scenes:
        scene_id = scene.get("id", "<missing-scene-id>")
        choices = scene.get("choices", [])
        echo_ids: set[str] = set()
        for echo in scene.get("state_echoes", []):
            echo_id = echo.get("id")
            if not echo_id:
                messages.append(ValidationMessage("error", scene_id, "State echo missing id"))
                continue
            if echo_id in echo_ids:
                messages.append(ValidationMessage("error", f"{scene_id}.{echo_id}", "Duplicate state echo id in scene"))
            echo_ids.add(echo_id)
            if not echo.get("text"):
                messages.append(ValidationMessage("error", f"{scene_id}.{echo_id}", "State echo missing text"))
            for requirement in echo.get("requirements", []):
                ref = requirement.get("state")
                if ref:
                    state_reads.add(ref)

        if len(choices) < 2:
            messages.append(ValidationMessage("warning", scene_id, "Scene should have at least 2 choices"))
        if len(choices) > 4:
            messages.append(ValidationMessage("warning", scene_id, "Scene should not exceed 4 choices"))

        for choice in choices:
            choice_id = choice.get("id")
            if not choice_id:
                messages.append(ValidationMessage("error", scene_id, "Choice missing id"))
                continue
            if choice_id in choice_ids:
                messages.append(ValidationMessage("error", f"{scene_id}.{choice_id}", "Duplicate choice id"))
            choice_ids.add(choice_id)
            target = choice.get("next_scene")
            if target not in scene_ids and target not in ending_ids:
                messages.append(ValidationMessage("error", f"{scene_id}.{choice_id}", f"next_scene target '{target}' does not exist"))
            for requirement in choice.get("requirements", []):
                ref = requirement.get("state")
                if ref:
                    state_reads.add(ref)
            collect_effect_writes(choice.get("effects", []), state_writes)

        unlocked: set[str] = set()
        for block in scene.get("background_blocks", []):
            text = block.get("text", "")
            for anchor in block.get("observe_anchors", []):
                validate_anchor(
                    anchor=anchor,
                    parent_text=text,
                    location=f"{scene_id}.{block.get('id', 'block')}",
                    messages=messages,
                    observe_ids=observe_ids,
                    guidance_ids=guidance_ids,
                    state_writes=state_writes,
                    unlocked_choices=unlocked,
                    depth_expected=1,
                )
        observe_unlocked_choices_by_scene[scene_id] = unlocked

    for scene in scenes:
        scene_id = scene.get("id", "<missing-scene-id>")
        scene_choice_ids = {choice.get("id") for choice in scene.get("choices", [])}
        for unlocked_choice in observe_unlocked_choices_by_scene.get(scene_id, set()):
            if unlocked_choice not in choice_ids:
                messages.append(ValidationMessage("error", f"{scene_id}.observe_unlocks", f"Unlocked choice '{unlocked_choice}' does not exist"))
            if unlocked_choice not in scene_choice_ids:
                messages.append(ValidationMessage("warning", f"{scene_id}.observe_unlocks", f"Unlocked choice '{unlocked_choice}' is outside current scene"))
        if scene.get("required_for_demo", True) and not (observe_unlocked_choices_by_scene.get(scene_id, set()) & scene_choice_ids):
            messages.append(ValidationMessage("warning", scene_id, "Main scene should include at least one observe-unlocked choice"))

    reachable = compute_reachable_scenes(game)
    for scene_id in scene_ids:
        if scene_id not in reachable:
            messages.append(ValidationMessage("warning", scene_id, "Scene is not reachable from start_scene_id"))

    for state_ref in sorted(state_reads - state_writes):
        messages.append(ValidationMessage("warning", state_ref, "State is read before any generated write"))
    return messages


def validate_anchor(
    anchor: dict[str, Any],
    parent_text: str,
    location: str,
    messages: list[ValidationMessage],
    observe_ids: set[str],
    guidance_ids: set[str],
    state_writes: set[str],
    unlocked_choices: set[str],
    depth_expected: int,
) -> None:
    anchor_id = anchor.get("id")
    if not anchor_id:
        messages.append(ValidationMessage("error", location, "Observe anchor missing id"))
        return
    anchor_location = f"{location}.{anchor_id}"
    if anchor_id in observe_ids:
        messages.append(ValidationMessage("error", anchor_location, "Duplicate observe anchor id"))
    observe_ids.add(anchor_id)

    depth = anchor.get("depth")
    if depth != depth_expected:
        messages.append(ValidationMessage("error", anchor_location, f"Expected depth {depth_expected}, got {depth}"))
    if not isinstance(depth, int) or depth < 1 or depth > 3:
        messages.append(ValidationMessage("error", anchor_location, "Observe depth must be between 1 and 3"))

    text_range = anchor.get("text_range", "")
    if text_range not in parent_text:
        messages.append(ValidationMessage("error", anchor_location, f"text_range '{text_range}' not found in parent text"))

    collect_effect_writes(anchor.get("effects", []), state_writes)
    for choice_id in anchor.get("unlocks_choices", []):
        unlocked_choices.add(choice_id)
    validate_guidance(anchor.get("guidance"), anchor_location, "guidance", guidance_ids, messages)
    validate_guidance(anchor.get("unlock_guidance"), anchor_location, "unlock_guidance", guidance_ids, messages)

    fragment = anchor.get("opens_fragment")
    if not isinstance(fragment, dict):
        messages.append(ValidationMessage("error", anchor_location, "Observe anchor must open a fragment"))
        return
    body = fragment.get("body", "")
    nested = fragment.get("nested_anchors", [])
    if depth == 3 and nested:
        messages.append(ValidationMessage("error", anchor_location, "Depth 3 anchor cannot contain nested anchors"))
    for child in nested:
        validate_anchor(
            anchor=child,
            parent_text=body,
            location=f"{anchor_location}.{fragment.get('id', 'fragment')}",
            messages=messages,
            observe_ids=observe_ids,
            guidance_ids=guidance_ids,
            state_writes=state_writes,
            unlocked_choices=unlocked_choices,
            depth_expected=depth_expected + 1,
        )


def validate_guidance(
    guidance: Any,
    anchor_location: str,
    field_name: str,
    guidance_ids: set[str],
    messages: list[ValidationMessage],
) -> None:
    if guidance is None:
        return
    location = f"{anchor_location}.{field_name}"
    if not isinstance(guidance, dict):
        messages.append(ValidationMessage("error", location, "Guidance must be an object"))
        return
    guidance_id = guidance.get("id")
    if not guidance_id:
        messages.append(ValidationMessage("error", location, "Guidance missing id"))
    elif guidance_id in guidance_ids:
        messages.append(ValidationMessage("error", location, "Duplicate guidance id"))
    else:
        guidance_ids.add(guidance_id)
    if not guidance.get("title"):
        messages.append(ValidationMessage("error", location, "Guidance missing title"))
    if not guidance.get("text"):
        messages.append(ValidationMessage("error", location, "Guidance missing text"))


def collect_effect_writes(effects: list[dict[str, Any]], state_writes: set[str]) -> None:
    for effect in effects:
        if "set" in effect and isinstance(effect["set"], dict):
            state_writes.update(effect["set"].keys())
        if "add" in effect and isinstance(effect["add"], dict):
            state_writes.update(effect["add"].keys())


def compute_reachable_scenes(game: dict[str, Any]) -> set[str]:
    scene_by_id = {scene.get("id"): scene for scene in game.get("scenes", [])}
    ending_ids = {ending.get("id") for ending in game.get("endings", []) if isinstance(ending, dict)}
    start = game.get("start_scene_id")
    pending = [start]
    seen: set[str] = set()
    while pending:
        scene_id = pending.pop()
        if scene_id in seen or scene_id not in scene_by_id:
            continue
        seen.add(scene_id)
        for choice in scene_by_id[scene_id].get("choices", []):
            target = choice.get("next_scene")
            if target and target not in ending_ids and target not in seen:
                pending.append(target)
    return seen


def build_path_map(game: dict[str, Any]) -> dict[str, Any]:
    scenes = []
    for scene in game.get("scenes", []):
        scene_choices = []
        for choice in scene.get("choices", []):
            scene_choices.append(
                {
                    "id": choice.get("id"),
                    "label": choice.get("label"),
                    "target": choice.get("next_scene"),
                    "requirements": choice.get("requirements", []),
                }
            )
        observes = []
        for block in scene.get("background_blocks", []):
            for anchor in block.get("observe_anchors", []):
                flatten_anchor(anchor, observes)
        echoes = []
        for echo in scene.get("state_echoes", []):
            echoes.append(
                {
                    "id": echo.get("id"),
                    "label": echo.get("label"),
                    "requirements": echo.get("requirements", []),
                }
            )
        scenes.append(
            {
                "id": scene.get("id"),
                "chapter": scene.get("chapter"),
                "title": scene.get("title"),
                "observes": observes,
                "state_echoes": echoes,
                "choices": scene_choices,
            }
        )
    return {"project": game.get("project", {}), "start_scene_id": game.get("start_scene_id"), "scenes": scenes}


def flatten_anchor(anchor: dict[str, Any], output: list[dict[str, Any]]) -> None:
    output.append(
        {
            "id": anchor.get("id"),
            "label": anchor.get("label"),
            "depth": anchor.get("depth"),
            "unlocks_choices": anchor.get("unlocks_choices", []),
        }
    )
    fragment = anchor.get("opens_fragment", {})
    for child in fragment.get("nested_anchors", []):
        flatten_anchor(child, output)


def write_validation_report(messages: list[ValidationMessage], path: str | Path) -> None:
    errors = [message for message in messages if message.level == "error"]
    warnings = [message for message in messages if message.level == "warning"]
    lines = [
        "# Validation Report",
        "",
        f"- Errors: {len(errors)}",
        f"- Warnings: {len(warnings)}",
        "",
    ]
    for message in messages:
        lines.append(f"- [{message.level.upper()}] `{message.location}`: {message.message}")
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")
