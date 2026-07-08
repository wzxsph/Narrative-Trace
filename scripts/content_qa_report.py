from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ALLOWED_DISCOVERABILITY = {"obvious", "subtle", "hidden_optional"}
CONSEQUENCE_LEVELS = {"local", "chapter", "global", "ending"}


@dataclass
class ContentQAMessage:
    level: str
    location: str
    message: str


def load_game(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def run_content_qa(game: dict[str, Any]) -> list[ContentQAMessage]:
    messages: list[ContentQAMessage] = []
    choices_by_id = {
        choice.get("id"): (scene, choice)
        for scene in game.get("scenes", [])
        for choice in scene.get("choices", [])
        if choice.get("id")
    }
    ending_ids = {ending.get("id") for ending in game.get("endings", []) if ending.get("id")}
    ending_choice_targets: dict[str, list[tuple[dict[str, Any], dict[str, Any]]]] = {
        ending_id: [] for ending_id in ending_ids
    }

    for scene in game.get("scenes", []):
        scene_id = scene.get("id", "<missing-scene-id>")
        anchors = collect_scene_anchors(scene)
        obvious_count = sum(1 for item in anchors if item["anchor"].get("discoverability") == "obvious")
        if scene.get("required_for_demo", True) and obvious_count == 0:
            messages.append(
                ContentQAMessage(
                    "error",
                    scene_id,
                    "Main scene must contain at least one obvious observe entry",
                )
            )

        scene_choice_ids = {choice.get("id") for choice in scene.get("choices", [])}
        unlocked_in_scene: set[str] = set()
        for item in anchors:
            anchor = item["anchor"]
            location = f"{scene_id}.{anchor.get('id', '<missing-anchor-id>')}"
            discoverability = anchor.get("discoverability")
            if discoverability not in ALLOWED_DISCOVERABILITY:
                messages.append(
                    ContentQAMessage(
                        "error",
                        location,
                        f"discoverability must be one of {sorted(ALLOWED_DISCOVERABILITY)}",
                    )
                )
            if not anchor.get("label"):
                messages.append(ContentQAMessage("error", location, "Observe anchor must have a label"))
            if len(str(anchor.get("text_range", ""))) < 2:
                messages.append(ContentQAMessage("warning", location, "Observe text_range is very short"))

            for choice_id in anchor.get("unlocks_choices", []):
                unlocked_in_scene.add(choice_id)
                choice_ref = choices_by_id.get(choice_id)
                if not choice_ref:
                    messages.append(ContentQAMessage("error", location, f"Unlocked choice '{choice_id}' does not exist"))
                    continue
                choice_scene, choice = choice_ref
                if choice_scene.get("id") != scene_id:
                    messages.append(ContentQAMessage("warning", location, f"Unlocked choice '{choice_id}' is outside current scene"))
                if discoverability == "hidden_optional" and choice.get("consequence_level") != "local":
                    messages.append(
                        ContentQAMessage(
                            "error",
                            location,
                            "hidden_optional observe must not unlock chapter/global consequence choices",
                        )
                    )

        if scene.get("required_for_demo", True) and not (unlocked_in_scene & scene_choice_ids):
            messages.append(
                ContentQAMessage(
                    "error",
                    scene_id,
                    "Main scene must include at least one observe-unlocked current-scene choice",
                )
            )

        for choice in scene.get("choices", []):
            validate_choice(scene_id, choice, messages)
            target = choice.get("next_scene")
            if target in ending_choice_targets:
                ending_choice_targets[target].append((scene, choice))

    validate_first_scene_guidance(game, messages)
    validate_endings(game, ending_choice_targets, messages)
    return messages


def collect_scene_anchors(scene: dict[str, Any]) -> list[dict[str, Any]]:
    anchors: list[dict[str, Any]] = []
    for block in scene.get("background_blocks", []):
        for anchor in block.get("observe_anchors", []):
            collect_anchor(anchor, anchors, parent_id=block.get("id", "block"))
    return anchors


def collect_anchor(anchor: dict[str, Any], anchors: list[dict[str, Any]], parent_id: str) -> None:
    anchors.append({"anchor": anchor, "parent_id": parent_id})
    fragment = anchor.get("opens_fragment", {})
    for child in fragment.get("nested_anchors", []):
        collect_anchor(child, anchors, parent_id=anchor.get("id", parent_id))


def validate_choice(scene_id: str, choice: dict[str, Any], messages: list[ContentQAMessage]) -> None:
    choice_id = choice.get("id", "<missing-choice-id>")
    location = f"{scene_id}.{choice_id}"
    if not choice.get("label"):
        messages.append(ContentQAMessage("error", location, "Choice must have a label"))
    if not choice.get("description"):
        messages.append(ContentQAMessage("error", location, "Choice must have a description"))
    if not choice.get("outcome"):
        messages.append(ContentQAMessage("error", location, "Choice must have an outcome"))

    consequence_level = choice.get("consequence_level")
    if consequence_level not in CONSEQUENCE_LEVELS:
        messages.append(
            ContentQAMessage(
                "error",
                location,
                f"consequence_level must be one of {sorted(CONSEQUENCE_LEVELS)}",
            )
        )
    if consequence_level in {"chapter", "global"}:
        if len(str(choice.get("description", ""))) < 12:
            messages.append(ContentQAMessage("warning", location, "Chapter/global choice description is too thin"))
        if len(str(choice.get("outcome", ""))) < 12:
            messages.append(ContentQAMessage("warning", location, "Chapter/global choice outcome is too thin"))


def validate_endings(
    game: dict[str, Any],
    ending_choice_targets: dict[str, list[tuple[dict[str, Any], dict[str, Any]]]],
    messages: list[ContentQAMessage],
) -> None:
    endings = game.get("endings", [])
    if len(endings) < 3:
        messages.append(ContentQAMessage("error", "game.endings", "Game should contain at least 3 main endings"))

    seen_tags: set[str] = set()
    for ending in endings:
        ending_id = ending.get("id", "<missing-ending-id>")
        location = f"ending.{ending_id}"
        if not ending.get("title"):
            messages.append(ContentQAMessage("error", location, "Ending must have a title"))
        if len(str(ending.get("body", ""))) < 24:
            messages.append(ContentQAMessage("error", location, "Ending body is too thin for a portrait"))

        tags = ending.get("tags", [])
        if not isinstance(tags, list) or len(tags) < 3:
            messages.append(ContentQAMessage("error", location, "Ending must include at least 3 portrait tags"))
        for tag in tags:
            if not isinstance(tag, str) or not tag:
                messages.append(ContentQAMessage("error", location, "Ending tags must be non-empty strings"))
                continue
            if tag in seen_tags:
                messages.append(ContentQAMessage("warning", location, f"Ending tag '{tag}' is reused"))
            seen_tags.add(tag)

        ending_choices = ending_choice_targets.get(ending_id, [])
        if not ending_choices:
            messages.append(ContentQAMessage("error", location, "Ending is not targeted by any choice"))
        for scene, choice in ending_choices:
            choice_location = f"{scene.get('id', '<missing-scene-id>')}.{choice.get('id', '<missing-choice-id>')}"
            if choice.get("consequence_level") != "ending":
                messages.append(ContentQAMessage("error", choice_location, "Choice targeting an ending must have consequence_level 'ending'"))
            if not choice_writes_state(choice):
                messages.append(ContentQAMessage("error", choice_location, "Choice targeting an ending must write at least one state value"))
            if len(str(choice.get("outcome", ""))) < 12:
                messages.append(ContentQAMessage("warning", choice_location, "Ending choice outcome is too thin"))


def choice_writes_state(choice: dict[str, Any]) -> bool:
    for effect in choice.get("effects", []):
        if effect.get("set") or effect.get("add"):
            return True
    return False


def validate_first_scene_guidance(game: dict[str, Any], messages: list[ContentQAMessage]) -> None:
    start_scene_id = game.get("start_scene_id")
    first_scene = next((scene for scene in game.get("scenes", []) if scene.get("id") == start_scene_id), None)
    if not first_scene:
        return
    anchors = [item["anchor"] for item in collect_scene_anchors(first_scene)]
    if not any(anchor.get("guidance") for anchor in anchors):
        messages.append(
            ContentQAMessage(
                "warning",
                start_scene_id,
                "First scene should include diegetic guidance for the first observe open",
            )
        )
    if not any(anchor.get("unlock_guidance") for anchor in anchors if anchor.get("unlocks_choices")):
        messages.append(
            ContentQAMessage(
                "warning",
                start_scene_id,
                "First scene should include diegetic guidance for the first observe-unlocked choice",
            )
        )


def format_report(messages: list[ContentQAMessage]) -> str:
    errors = [message for message in messages if message.level == "error"]
    warnings = [message for message in messages if message.level == "warning"]
    lines = [
        "# Content QA Report",
        "",
        f"- Errors: {len(errors)}",
        f"- Warnings: {len(warnings)}",
        "",
    ]
    for message in messages:
        lines.append(f"- {message.level.upper()} `{message.location}`: {message.message}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if len(args) != 1:
        print("Usage: python3 scripts/content_qa_report.py <game.json>")
        return 2
    messages = run_content_qa(load_game(args[0]))
    print(format_report(messages))
    return 1 if any(message.level == "error" for message in messages) else 0


if __name__ == "__main__":
    raise SystemExit(main())
