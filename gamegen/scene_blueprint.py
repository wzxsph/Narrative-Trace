from __future__ import annotations

from collections import Counter, deque
from dataclasses import dataclass
from typing import Any, Literal


Level = Literal["error", "warning"]

REQUIRED_TOP_LEVEL_FIELDS = {
    "schema_version",
    "project_id",
    "source_plan_schema_version",
    "source_state_schema_design_version",
    "entry_scene_id",
    "scenes",
    "ending_targets",
}
REQUIRED_SCENE_FIELDS = {
    "id",
    "chapter_id",
    "title",
    "scene_role",
    "required_state_reads",
    "state_writes",
    "observe_targets",
    "choice_targets",
    "next_scene_ids",
    "ending_targets",
}


@dataclass(frozen=True)
class SceneBlueprintMessage:
    level: Level
    location: str
    message: str


def build_scene_blueprint_design(
    brief: dict[str, Any],
    generation_plan: dict[str, Any],
    state_schema_design: dict[str, Any],
) -> dict[str, Any]:
    project = brief["project"]
    scene_specs = [
        scene_blueprint(
            "ch01_phone_lock",
            "ch01",
            "锁屏上的半句话",
            "entry_mystery",
            ["clues.unsent_warning", "clues.station_location"],
            ["clues.unsent_warning", "clues.station_location", "relationships.chen.trust", "relationships.chen.suspicion"],
            ["obs_unsent_sms", "obs_0213_log", "obs_remote_wipe", "obs_pause_window"],
            ["choice_call_chen", "choice_go_station", "choice_delay_wipe", "choice_confront_chen"],
            ["ch01_cloud_console", "ch01_contact_trace"],
        ),
        scene_blueprint(
            "ch01_cloud_console",
            "ch01",
            "云端控制台",
            "pressure_escalation",
            ["clues.wipe_pause_window", "clues.freeze_token"],
            ["clues.freeze_token", "pressure.company_alert", "stance.protect_person"],
            ["obs_device_admin", "obs_session_token", "obs_screen_recording"],
            ["choice_freeze_wipe", "choice_isolate_phone", "choice_leave_unfrozen"],
            ["ch01_contact_trace"],
        ),
        scene_blueprint(
            "ch01_contact_trace",
            "ch01",
            "联系人里的陈",
            "relationship_probe",
            ["relationships.chen.trust", "relationships.chen.suspicion"],
            ["relationships.chen.trust", "relationships.lin.bond", "stance.truth_first"],
            ["obs_chen_alias", "obs_casefile_share", "obs_taxi_order", "obs_voice_note"],
            ["choice_leave_for_station", "choice_send_voice_to_self", "choice_warn_chen"],
            ["ch02_station_gate"],
        ),
        scene_blueprint(
            "ch02_station_gate",
            "ch02",
            "旧员工入口",
            "threshold_choice",
            ["clues.station_entry_code", "pressure.company_alert"],
            ["clues.station_entry_code", "stance.truth_first", "stance.protect_person"],
            ["obs_station_entry_code", "obs_security_booth", "obs_camera_blind_spot"],
            ["choice_enter_service_corridor", "choice_wait_guard_shift", "choice_call_chen_at_gate"],
            ["ch02_station_platform"],
        ),
        scene_blueprint(
            "ch02_station_platform",
            "ch02",
            "废弃站台",
            "evidence_reveal",
            ["clues.locker_a17", "clues.victim_list"],
            ["clues.locker_a17", "relationships.lin.bond", "stance.protect_person"],
            ["obs_ticket", "obs_locker_code", "obs_red_dot", "obs_recording_warning"],
            ["choice_wait_station", "choice_open_locker", "choice_cover_camera"],
            ["ch02_locker_room"],
        ),
        scene_blueprint(
            "ch02_locker_room",
            "ch02",
            "储物柜后的维护间",
            "asset_recovery",
            ["clues.backup_copy", "relationships.lin.bond"],
            ["clues.backup_copy", "relationships.lin.bond"],
            ["obs_backup_drive", "obs_audio_key", "obs_red_bracelet"],
            ["choice_take_backup_to_safehouse", "choice_protect_lin_secret", "choice_destroy_locker_camera"],
            ["ch03_backup_unlock"],
        ),
        scene_blueprint(
            "ch03_backup_unlock",
            "ch03",
            "解密备份",
            "context_reframe",
            ["clues.backup_copy", "clues.victim_list"],
            ["clues.victim_list", "stance.truth_first", "stance.protect_person"],
            ["obs_raw_recording", "obs_edited_recording", "obs_context_chain"],
            ["choice_compare_context", "choice_send_hash_to_chen", "choice_archive_first"],
            ["ch03_witness_thread", "ch03_publish_decision"],
        ),
        scene_blueprint(
            "ch03_witness_thread",
            "ch03",
            "最后留言串",
            "relationship_echo",
            ["relationships.chen.trust", "relationships.chen.suspicion", "relationships.lin.bond"],
            ["clues.public_packet_ready", "clues.archive_ready", "clues.chen_message_ready", "relationships.chen.trust"],
            ["obs_final_message", "obs_victim_list", "obs_chen_pause"],
            ["choice_prepare_public_packet", "choice_prepare_archive", "choice_ask_chen_last_time"],
            ["ch03_publish_decision"],
        ),
        scene_blueprint(
            "ch03_publish_decision",
            "ch03",
            "发布页",
            "ending_matrix",
            ["clues.public_packet_ready", "clues.archive_ready", "clues.chen_message_ready"],
            ["stance.truth_first", "stance.protect_person", "pressure.company_alert"],
            ["obs_public_packet", "obs_offline_archive"],
            ["choice_publish_truth", "choice_keep_archive", "choice_confront_final"],
            [],
            ending_targets=generation_plan["ending_targets"],
        ),
    ]
    return {
        "schema_version": "scene_blueprint_v0_1",
        "project_id": project["id"],
        "source_plan_schema_version": generation_plan["plan_schema_version"],
        "source_state_schema_design_version": state_schema_design["schema_version"],
        "entry_scene_id": scene_specs[0]["id"],
        "scenes": scene_specs,
        "ending_targets": generation_plan["ending_targets"],
    }


def scene_blueprint(
    scene_id: str,
    chapter_id: str,
    title: str,
    scene_role: str,
    required_state_reads: list[str],
    state_writes: list[str],
    observe_targets: list[str],
    choice_targets: list[str],
    next_scene_ids: list[str],
    ending_targets: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "id": scene_id,
        "chapter_id": chapter_id,
        "title": title,
        "scene_role": scene_role,
        "required_state_reads": required_state_reads,
        "state_writes": state_writes,
        "observe_targets": observe_targets,
        "choice_targets": choice_targets,
        "next_scene_ids": next_scene_ids,
        "ending_targets": ending_targets or [],
    }


def validate_scene_blueprint_design(
    blueprint: dict[str, Any],
    generation_plan: dict[str, Any],
    state_schema_design: dict[str, Any],
) -> list[SceneBlueprintMessage]:
    messages: list[SceneBlueprintMessage] = []
    for field in sorted(REQUIRED_TOP_LEVEL_FIELDS):
        if field not in blueprint:
            messages.append(SceneBlueprintMessage("error", field, "Missing required top-level field"))

    if blueprint.get("schema_version") != "scene_blueprint_v0_1":
        messages.append(
            SceneBlueprintMessage("error", "schema_version", "Scene blueprint must use scene_blueprint_v0_1")
        )

    scenes = blueprint.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        messages.append(SceneBlueprintMessage("error", "scenes", "Scenes must be a non-empty list"))
        return messages

    scene_ids = _validate_scenes(scenes, generation_plan, state_schema_design, messages)
    _validate_entry_and_reachability(blueprint, scenes, scene_ids, messages)
    _validate_chapter_budgets(scenes, generation_plan, messages)
    _validate_ending_coverage(blueprint, scenes, generation_plan, messages)
    return messages


def _validate_scenes(
    scenes: list[Any],
    generation_plan: dict[str, Any],
    state_schema_design: dict[str, Any],
    messages: list[SceneBlueprintMessage],
) -> set[str]:
    scene_ids: set[str] = set()
    chapter_ids = {chapter.get("id") for chapter in generation_plan.get("chapters", [])}
    state_keys = {variable.get("key") for variable in state_schema_design.get("variables", [])}
    for index, scene in enumerate(scenes):
        location = f"scenes[{index}]"
        if not isinstance(scene, dict):
            messages.append(SceneBlueprintMessage("error", location, "Scene blueprint must be an object"))
            continue
        for field in sorted(REQUIRED_SCENE_FIELDS):
            if field not in scene:
                messages.append(SceneBlueprintMessage("error", f"{location}.{field}", "Missing scene field"))
        scene_id = scene.get("id")
        if not isinstance(scene_id, str) or not scene_id:
            messages.append(SceneBlueprintMessage("error", f"{location}.id", "Scene id must be a string"))
        elif scene_id in scene_ids:
            messages.append(SceneBlueprintMessage("error", f"{location}.id", f"Duplicate scene id: {scene_id}"))
        elif not scene_id.startswith(str(scene.get("chapter_id", ""))):
            messages.append(SceneBlueprintMessage("warning", f"{location}.id", "Scene id should start with chapter id"))
        if isinstance(scene_id, str) and scene_id:
            scene_ids.add(scene_id)

        chapter_id = scene.get("chapter_id")
        if chapter_id not in chapter_ids:
            messages.append(SceneBlueprintMessage("error", f"{location}.chapter_id", f"Unknown chapter id: {chapter_id}"))

        for list_field in ("required_state_reads", "state_writes", "observe_targets", "choice_targets", "next_scene_ids", "ending_targets"):
            value = scene.get(list_field)
            if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
                messages.append(SceneBlueprintMessage("error", f"{location}.{list_field}", f"{list_field} must be a list of ids"))

        if not scene.get("observe_targets"):
            messages.append(SceneBlueprintMessage("error", f"{location}.observe_targets", "Scene must plan at least one observe"))
        if not scene.get("choice_targets"):
            messages.append(SceneBlueprintMessage("error", f"{location}.choice_targets", "Scene must plan at least one choice"))

        for field in ("required_state_reads", "state_writes"):
            for state_key in scene.get(field, []):
                if state_key not in state_keys:
                    messages.append(
                        SceneBlueprintMessage("error", f"{location}.{field}", f"Unknown state variable: {state_key}")
                    )
    return scene_ids


def _validate_entry_and_reachability(
    blueprint: dict[str, Any],
    scenes: list[Any],
    scene_ids: set[str],
    messages: list[SceneBlueprintMessage],
) -> None:
    entry_scene_id = blueprint.get("entry_scene_id")
    if entry_scene_id not in scene_ids:
        messages.append(SceneBlueprintMessage("error", "entry_scene_id", f"Unknown entry scene: {entry_scene_id}"))
        return

    for index, scene in enumerate(scenes):
        if not isinstance(scene, dict):
            continue
        for next_scene_id in scene.get("next_scene_ids", []):
            if next_scene_id not in scene_ids:
                messages.append(
                    SceneBlueprintMessage("error", f"scenes[{index}].next_scene_ids", f"Unknown next scene: {next_scene_id}")
                )

    scene_by_id = {scene["id"]: scene for scene in scenes if isinstance(scene, dict) and isinstance(scene.get("id"), str)}
    reachable = {entry_scene_id}
    queue: deque[str] = deque([entry_scene_id])
    while queue:
        current_id = queue.popleft()
        for next_scene_id in scene_by_id.get(current_id, {}).get("next_scene_ids", []):
            if next_scene_id not in reachable:
                reachable.add(next_scene_id)
                queue.append(next_scene_id)
    for scene_id in sorted(scene_ids - reachable):
        messages.append(SceneBlueprintMessage("error", "scenes", f"Unreachable scene: {scene_id}"))


def _validate_chapter_budgets(
    scenes: list[Any],
    generation_plan: dict[str, Any],
    messages: list[SceneBlueprintMessage],
) -> None:
    counts = Counter(scene.get("chapter_id") for scene in scenes if isinstance(scene, dict))
    for chapter in generation_plan.get("chapters", []):
        chapter_id = chapter.get("id")
        expected = chapter.get("scene_budget")
        if expected is not None and counts[chapter_id] != expected:
            messages.append(
                SceneBlueprintMessage(
                    "error",
                    f"chapters.{chapter_id}.scene_budget",
                    f"Expected {expected} scenes, got {counts[chapter_id]}",
                )
            )

    expected_count = generation_plan.get("scene_count")
    if expected_count is not None and len(scenes) != expected_count:
        messages.append(SceneBlueprintMessage("error", "scenes", f"Expected {expected_count} scenes, got {len(scenes)}"))


def _validate_ending_coverage(
    blueprint: dict[str, Any],
    scenes: list[Any],
    generation_plan: dict[str, Any],
    messages: list[SceneBlueprintMessage],
) -> None:
    expected_endings = set(generation_plan.get("ending_targets", []))
    declared_endings = set(blueprint.get("ending_targets", []))
    if declared_endings != expected_endings:
        messages.append(SceneBlueprintMessage("error", "ending_targets", "Blueprint ending targets must match generation plan"))

    covered_endings: set[str] = set()
    for index, scene in enumerate(scenes):
        scene_endings = set(scene.get("ending_targets", [])) if isinstance(scene, dict) else set()
        unknown = scene_endings - expected_endings
        for ending_id in sorted(unknown):
            messages.append(SceneBlueprintMessage("error", f"scenes[{index}].ending_targets", f"Unknown ending target: {ending_id}"))
        covered_endings.update(scene_endings)

    for ending_id in sorted(expected_endings - covered_endings):
        messages.append(SceneBlueprintMessage("error", "scenes.ending_targets", f"Ending target is not covered: {ending_id}"))
