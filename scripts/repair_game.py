#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import difflib
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from gamegen.validator import load_game, validate_game


def repair_game(game: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    repaired = copy.deepcopy(game)
    repairs: list[str] = []
    repair_start_scene(repaired, repairs)
    repair_choice_targets(repaired, repairs)
    repair_anchor_refs_and_ranges(repaired, repairs)
    return repaired, repairs


def repair_start_scene(game: dict[str, Any], repairs: list[str]) -> None:
    scene_ids = [scene.get("id") for scene in game.get("scenes", []) if scene.get("id")]
    if not scene_ids:
        return
    if game.get("start_scene_id") not in scene_ids:
        old_value = game.get("start_scene_id")
        game["start_scene_id"] = scene_ids[0]
        repairs.append(f"game.start_scene_id: replaced {old_value!r} with {scene_ids[0]!r}")


def repair_choice_targets(game: dict[str, Any], repairs: list[str]) -> None:
    scenes = game.get("scenes", [])
    scene_ids = [scene.get("id") for scene in scenes if scene.get("id")]
    ending_ids = [ending.get("id") for ending in game.get("endings", []) if ending.get("id")]
    valid_targets = scene_ids + ending_ids
    if not valid_targets:
        return

    for scene_index, scene in enumerate(scenes):
        fallback = next_scene_or_ending(scene_index, scene_ids, ending_ids)
        for choice in scene.get("choices", []):
            target = choice.get("next_scene")
            if target in valid_targets:
                continue
            replacement = closest_id(str(target or ""), valid_targets) or fallback
            if replacement:
                choice["next_scene"] = replacement
                repairs.append(
                    f"{scene.get('id')}.{choice.get('id')}.next_scene: replaced {target!r} with {replacement!r}"
                )


def next_scene_or_ending(scene_index: int, scene_ids: list[str], ending_ids: list[str]) -> str | None:
    if scene_index + 1 < len(scene_ids):
        return scene_ids[scene_index + 1]
    if ending_ids:
        return ending_ids[0]
    if scene_ids:
        return scene_ids[0]
    return None


def repair_anchor_refs_and_ranges(game: dict[str, Any], repairs: list[str]) -> None:
    choice_ids = [
        choice.get("id")
        for scene in game.get("scenes", [])
        for choice in scene.get("choices", [])
        if choice.get("id")
    ]
    for scene in game.get("scenes", []):
        scene_id = scene.get("id", "<missing-scene-id>")
        for block in scene.get("background_blocks", []):
            repair_anchors_in_parent(
                anchors=block.get("observe_anchors", []),
                parent=block,
                text_key="text",
                expected_depth=1,
                choice_ids=choice_ids,
                repairs=repairs,
                location=f"{scene_id}.{block.get('id', 'block')}",
            )


def repair_anchors_in_parent(
    anchors: list[dict[str, Any]],
    parent: dict[str, Any],
    text_key: str,
    expected_depth: int,
    choice_ids: list[str],
    repairs: list[str],
    location: str,
) -> None:
    parent_text = str(parent.get(text_key, ""))
    for anchor in anchors:
        anchor_id = anchor.get("id", "<missing-anchor-id>")
        anchor_location = f"{location}.{anchor_id}"
        if anchor.get("depth") != expected_depth:
            old_depth = anchor.get("depth")
            anchor["depth"] = expected_depth
            repairs.append(f"{anchor_location}.depth: replaced {old_depth!r} with {expected_depth!r}")

        text_range = anchor.get("text_range")
        if isinstance(text_range, str) and text_range and text_range not in parent_text:
            parent_text = append_missing_text_range(parent_text, text_range)
            parent[text_key] = parent_text
            repairs.append(f"{anchor_location}.text_range: inserted {text_range!r} into parent text")

        anchor["unlocks_choices"] = repair_choice_id_list(
            anchor.get("unlocks_choices", []),
            choice_ids,
            f"{anchor_location}.unlocks_choices",
            repairs,
        )

        fragment = anchor.get("opens_fragment")
        if isinstance(fragment, dict):
            repair_anchors_in_parent(
                anchors=fragment.get("nested_anchors", []),
                parent=fragment,
                text_key="body",
                expected_depth=expected_depth + 1,
                choice_ids=choice_ids,
                repairs=repairs,
                location=f"{anchor_location}.{fragment.get('id', 'fragment')}",
            )


def repair_choice_id_list(
    ids: list[str],
    valid_choice_ids: list[str],
    location: str,
    repairs: list[str],
) -> list[str]:
    repaired_ids: list[str] = []
    for choice_id in ids:
        if choice_id in valid_choice_ids:
            repaired_ids.append(choice_id)
            continue
        replacement = closest_id(str(choice_id or ""), valid_choice_ids)
        if replacement:
            repaired_ids.append(replacement)
            repairs.append(f"{location}: replaced {choice_id!r} with {replacement!r}")
        else:
            repairs.append(f"{location}: removed invalid choice id {choice_id!r}")
    return repaired_ids


def append_missing_text_range(parent_text: str, text_range: str) -> str:
    if not parent_text:
        return text_range
    separator = "" if parent_text.endswith((" ", "\n")) else " "
    return f"{parent_text}{separator}{text_range}"


def closest_id(value: str, candidates: list[str]) -> str | None:
    matches = difflib.get_close_matches(value, candidates, n=1, cutoff=0.78)
    return matches[0] if matches else None


def validation_errors(game: dict[str, Any]) -> list[str]:
    return [
        f"{message.location}: {message.message}"
        for message in validate_game(game)
        if message.level == "error"
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description="Conservatively repair local structural errors in a generated game.")
    parser.add_argument("game_json", help="Path to generated game.json")
    parser.add_argument("--out", help="Write repaired game JSON to this path")
    parser.add_argument("--in-place", action="store_true", help="Overwrite the input game JSON")
    args = parser.parse_args()

    source_path = Path(args.game_json)
    game = load_game(source_path)
    before_errors = validation_errors(game)
    repaired, repairs = repair_game(game)
    after_errors = validation_errors(repaired)

    if not repairs:
        print("No repair needed: no supported repair targets found")
    else:
        print("Applied repairs:")
        for repair in repairs:
            print(f"- {repair}")

    if after_errors:
        print("Remaining validation errors:")
        for error in after_errors:
            print(f"- {error}")

    target_path: Path | None = None
    if args.in_place:
        target_path = source_path
    elif args.out:
        target_path = Path(args.out)

    if target_path:
        target_path.write_text(json.dumps(repaired, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote repaired game to {target_path}")
    elif repairs:
        print("No file written. Pass --out or --in-place to persist repairs.")

    if before_errors and not after_errors:
        print("Repair successful: validation has no errors")
    elif not before_errors:
        print("Validation already had no errors")

    return 1 if after_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
