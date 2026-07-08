from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SAVE_CONTRACT = ROOT / "examples" / "fixtures" / "save_contract" / "save_cases.json"


def load_save_contract(path: str | Path = DEFAULT_SAVE_CONTRACT) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def validate_save_contract(path: str | Path = DEFAULT_SAVE_CONTRACT) -> list[str]:
    contract_path = Path(path)
    contract = load_save_contract(contract_path)
    errors: list[str] = []

    if contract.get("schema_version") != "game_writer_save_contract_v0_1":
        errors.append("Unsupported save contract schema_version")
    current_version = contract.get("current_save_version")
    if current_version != 2:
        errors.append("current_save_version must match runtime SAVE_VERSION 2")
    if contract.get("save_key") != "game_writer_missing_phone_runtime_v1":
        errors.append("save_key must match runtime SAVE_KEY")

    game_path = ROOT / str(contract.get("base_game", ""))
    if not game_path.exists():
        errors.append(f"base_game not found: {game_path}")
        return errors
    game = json.loads(game_path.read_text(encoding="utf-8"))

    seen_ids: set[str] = set()
    cases = contract.get("cases", [])
    if not isinstance(cases, list) or not cases:
        errors.append("cases must be a non-empty array")
        return errors

    for index, case in enumerate(cases):
        location = f"cases[{index}]"
        if not isinstance(case, dict):
            errors.append(f"{location}: case must be an object")
            continue
        case_id = case.get("id")
        if not isinstance(case_id, str) or not case_id:
            errors.append(f"{location}: missing id")
            continue
        if case_id in seen_ids:
            errors.append(f"{case_id}: duplicate id")
        seen_ids.add(case_id)

        expect = case.get("expect", {})
        if not isinstance(expect, dict):
            errors.append(f"{case_id}: expect must be an object")
            continue

        if "raw_save" in case:
            errors.extend(validate_raw_save_case(case, expect))
            continue

        payload = case.get("payload")
        if not isinstance(payload, dict):
            errors.append(f"{case_id}: payload must be an object")
            continue

        migrated = migrate_save_payload(payload, current_version)
        should_restore = bool(expect.get("restores"))
        if should_restore:
            if migrated is None:
                errors.append(f"{case_id}: expected restore but migration returned null")
                continue
            expected_version = expect.get("migrated_version")
            if expected_version != migrated.get("version"):
                errors.append(f"{case_id}: migrated_version mismatch")
            errors.extend(validate_save_payload(migrated, game, current_version, case_id))
            expected_screen = expect.get("screen")
            if expected_screen == "review" and not migrated.get("review"):
                errors.append(f"{case_id}: expected review screen but review is empty")
            if expected_screen == "ending" and not migrated.get("endingId"):
                errors.append(f"{case_id}: expected ending screen but endingId is empty")
        else:
            if migrated is not None and not validate_save_payload(migrated, game, current_version, case_id):
                errors.append(f"{case_id}: expected fallback but payload is restorable")
            if not expect.get("recovery_notice_contains"):
                errors.append(f"{case_id}: fallback case must declare recovery_notice_contains")

    return errors


def validate_raw_save_case(case: dict[str, Any], expect: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    case_id = str(case.get("id", "<missing>"))
    raw_save = case.get("raw_save")
    if not isinstance(raw_save, str):
        errors.append(f"{case_id}: raw_save must be a string")
        return errors
    try:
        json.loads(raw_save)
    except json.JSONDecodeError:
        if expect.get("restores"):
            errors.append(f"{case_id}: invalid raw_save cannot restore")
        if not expect.get("recovery_notice_contains"):
            errors.append(f"{case_id}: corrupt raw_save must declare recovery_notice_contains")
        return errors
    errors.append(f"{case_id}: raw_save is valid JSON; use payload instead")
    return errors


def migrate_save_payload(payload: dict[str, Any] | None, current_version: int) -> dict[str, Any] | None:
    if not isinstance(payload, dict):
        return None
    if payload.get("version") == current_version:
        return dict(payload)
    if payload.get("version") == 1 and current_version == 2:
        migrated = dict(payload)
        migrated["version"] = current_version
        return migrated
    return None


def validate_save_payload(payload: dict[str, Any], game: dict[str, Any], current_version: int, case_id: str) -> list[str]:
    errors: list[str] = []
    scene_ids = {scene["id"] for scene in game.get("scenes", [])}
    ending_ids = {ending["id"] for ending in game.get("endings", [])}
    choice_ids = {choice["id"] for scene in game.get("scenes", []) for choice in scene.get("choices", [])}

    if payload.get("version") != current_version:
        errors.append(f"{case_id}: payload version must be {current_version}")
    if payload.get("projectId") != (game.get("project", {}).get("id") or ""):
        errors.append(f"{case_id}: projectId mismatch")
    if payload.get("schemaVersion") != game.get("schema_version"):
        errors.append(f"{case_id}: schemaVersion mismatch")
    if payload.get("sceneId") not in scene_ids:
        errors.append(f"{case_id}: sceneId does not exist")
    ending_id = payload.get("endingId")
    if ending_id and ending_id not in ending_ids:
        errors.append(f"{case_id}: endingId does not exist")

    review = payload.get("review")
    if review:
        if not isinstance(review, dict):
            errors.append(f"{case_id}: review must be an object or null")
        else:
            if review.get("fromSceneId") not in scene_ids:
                errors.append(f"{case_id}: review.fromSceneId does not exist")
            if review.get("nextSceneId") not in scene_ids:
                errors.append(f"{case_id}: review.nextSceneId does not exist")
            if review.get("choiceId") not in choice_ids:
                errors.append(f"{case_id}: review.choiceId does not exist")

    if not isinstance(payload.get("state"), dict):
        errors.append(f"{case_id}: state must be an object")
    for field in (
        "openedAnchors",
        "unlockedChoices",
        "seenGuidance",
        "highlightedChoices",
        "visitedScenes",
        "chosenChoices",
        "choiceOutcomes",
    ):
        if not isinstance(payload.get(field), list):
            errors.append(f"{case_id}: {field} must be an array")
    active_guidance = payload.get("activeGuidance")
    if active_guidance is not None and not isinstance(active_guidance, dict):
        errors.append(f"{case_id}: activeGuidance must be object or null")

    return errors
