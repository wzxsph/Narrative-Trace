from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal


Level = Literal["error", "warning"]


@dataclass(frozen=True)
class BlueprintAlignmentMessage:
    level: Level
    location: str
    message: str


def validate_blueprint_alignment(
    game: dict[str, Any],
    scene_blueprint: dict[str, Any],
) -> list[BlueprintAlignmentMessage]:
    messages: list[BlueprintAlignmentMessage] = []
    scene_by_id = {scene.get("id"): scene for scene in game.get("scenes", []) if isinstance(scene, dict)}
    ending_ids = {ending.get("id") for ending in game.get("endings", []) if isinstance(ending, dict)}

    entry_scene_id = scene_blueprint.get("entry_scene_id")
    if game.get("start_scene_id") != entry_scene_id:
        messages.append(
            BlueprintAlignmentMessage(
                "error",
                "start_scene_id",
                f"Game start_scene_id must match blueprint entry_scene_id: {entry_scene_id}",
            )
        )

    for index, blueprint_scene in enumerate(scene_blueprint.get("scenes", [])):
        location = f"scenes[{index}]"
        if not isinstance(blueprint_scene, dict):
            messages.append(BlueprintAlignmentMessage("error", location, "Blueprint scene must be an object"))
            continue

        scene_id = blueprint_scene.get("id")
        game_scene = scene_by_id.get(scene_id)
        if not game_scene:
            messages.append(BlueprintAlignmentMessage("error", f"{location}.id", f"Game is missing blueprint scene: {scene_id}"))
            continue

        if game_scene.get("title") != blueprint_scene.get("title"):
            messages.append(
                BlueprintAlignmentMessage("warning", f"{location}.title", f"Game scene title differs from blueprint: {scene_id}")
            )

        observe_ids = collect_observe_ids(game_scene)
        choice_ids = {choice.get("id") for choice in game_scene.get("choices", []) if isinstance(choice, dict)}
        choice_next_targets = {
            choice.get("next_scene") for choice in game_scene.get("choices", []) if isinstance(choice, dict)
        }
        state_writes = collect_state_writes(game_scene)

        for observe_id in blueprint_scene.get("observe_targets", []):
            if observe_id not in observe_ids:
                messages.append(
                    BlueprintAlignmentMessage(
                        "error",
                        f"{location}.observe_targets",
                        f"Game scene {scene_id} is missing planned observe: {observe_id}",
                    )
                )

        for choice_id in blueprint_scene.get("choice_targets", []):
            if choice_id not in choice_ids:
                messages.append(
                    BlueprintAlignmentMessage(
                        "error",
                        f"{location}.choice_targets",
                        f"Game scene {scene_id} is missing planned choice: {choice_id}",
                    )
                )

        for next_scene_id in blueprint_scene.get("next_scene_ids", []):
            if next_scene_id not in choice_next_targets:
                messages.append(
                    BlueprintAlignmentMessage(
                        "error",
                        f"{location}.next_scene_ids",
                        f"Game scene {scene_id} has no choice path to planned next scene: {next_scene_id}",
                    )
                )

        for ending_id in blueprint_scene.get("ending_targets", []):
            if ending_id not in ending_ids:
                messages.append(
                    BlueprintAlignmentMessage(
                        "error",
                        f"{location}.ending_targets",
                        f"Game is missing planned ending: {ending_id}",
                    )
                )
            elif ending_id not in choice_next_targets:
                messages.append(
                    BlueprintAlignmentMessage(
                        "error",
                        f"{location}.ending_targets",
                        f"Game scene {scene_id} has no choice path to planned ending: {ending_id}",
                    )
                )

        for state_key in blueprint_scene.get("state_writes", []):
            if state_key not in state_writes:
                messages.append(
                    BlueprintAlignmentMessage(
                        "error",
                        f"{location}.state_writes",
                        f"Game scene {scene_id} does not write planned state: {state_key}",
                    )
                )

    blueprint_scene_ids = {
        scene.get("id") for scene in scene_blueprint.get("scenes", []) if isinstance(scene, dict)
    }
    for scene_id in sorted(set(scene_by_id) - blueprint_scene_ids):
        messages.append(BlueprintAlignmentMessage("warning", "game.scenes", f"Game has scene outside blueprint: {scene_id}"))

    return messages


def collect_observe_ids(scene: dict[str, Any]) -> set[str]:
    observe_ids: set[str] = set()
    for block in scene.get("background_blocks", []):
        if not isinstance(block, dict):
            continue
        for anchor in block.get("observe_anchors", []):
            observe_ids.update(_collect_anchor_ids(anchor))
    return observe_ids


def collect_state_writes(scene: dict[str, Any]) -> set[str]:
    state_writes: set[str] = set()
    for block in scene.get("background_blocks", []):
        if not isinstance(block, dict):
            continue
        for anchor in block.get("observe_anchors", []):
            state_writes.update(_collect_anchor_state_writes(anchor))
    for choice in scene.get("choices", []):
        if isinstance(choice, dict):
            state_writes.update(_collect_effect_state_writes(choice.get("effects", [])))
    return state_writes


def _collect_anchor_ids(anchor: Any) -> set[str]:
    if not isinstance(anchor, dict):
        return set()
    ids = {anchor["id"]} if isinstance(anchor.get("id"), str) else set()
    fragment = anchor.get("opens_fragment", {})
    if isinstance(fragment, dict):
        for nested in fragment.get("nested_anchors", []):
            ids.update(_collect_anchor_ids(nested))
    return ids


def _collect_anchor_state_writes(anchor: Any) -> set[str]:
    if not isinstance(anchor, dict):
        return set()
    state_writes = _collect_effect_state_writes(anchor.get("effects", []))
    fragment = anchor.get("opens_fragment", {})
    if isinstance(fragment, dict):
        for nested in fragment.get("nested_anchors", []):
            state_writes.update(_collect_anchor_state_writes(nested))
    return state_writes


def _collect_effect_state_writes(effects: Any) -> set[str]:
    state_writes: set[str] = set()
    if not isinstance(effects, list):
        return state_writes
    for effect in effects:
        if not isinstance(effect, dict):
            continue
        for operation in ("set", "add"):
            values = effect.get(operation)
            if isinstance(values, dict):
                state_writes.update(key for key in values if isinstance(key, str))
    return state_writes
