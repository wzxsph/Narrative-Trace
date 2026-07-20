from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from .kernel_contract import file_digest
from .prompt_manifest import active_prompt_set_id


KERNEL_VERSION = "1.0.0"
GAME_SCHEMA_VERSION = "narrative_game_v1"
PACK_SCHEMA_VERSION = "narrative_content_pack_v1"
STATE_SCHEMA_VERSION = "narrative_state_registry_v1"
PROVENANCE_SCHEMA_VERSION = "narrative_provenance_v1"


STATE_LABELS = {
    "clues.archive_ready": "归档包",
    "clues.backup_copy": "备份副本",
    "clues.chen_casefile": "陈的旧案卷",
    "clues.chen_message_ready": "给陈的草稿",
    "clues.chen_motive": "陈的动机",
    "clues.chen_trimmed_location": "定位截断记录",
    "clues.cloud_admin": "云端管理员来源",
    "clues.edited_recording": "剪辑录音",
    "clues.final_message": "最后留言",
    "clues.freeze_token": "冻结令牌",
    "clues.hidden_camera": "隐藏摄像头",
    "clues.lin_confession": "林的自述",
    "clues.locker_a17": "A17 储物柜",
    "clues.public_packet_ready": "公开包",
    "clues.raw_recording": "原始录音",
    "clues.screen_recording": "屏幕录制会话",
    "clues.security_booth": "保安岗亭",
    "clues.station_entry_code": "旧员工入口码",
    "clues.station_location": "废弃地铁站定位",
    "clues.station_route_confirmed": "订单路线",
    "clues.victim_list": "受害者名单",
    "clues.voice_note": "语音便签",
    "clues.wipe_pause_window": "远程清除暂停窗口",
    "stance.truth_first": "真相优先",
    "stance.protect_person": "保护具体的人",
    "relationships.chen.trust": "陈的信任",
    "relationships.chen.suspicion": "陈的怀疑",
    "relationships.lin.bond": "与林的关联",
    "pressure.company_alert": "公司警觉",
}


ENDING_PORTRAITS = {
    "ending_publish": {
        "protected": ["林与受害者的证据"],
        "harmed": ["陈警官及被公开材料牵连的人"],
        "believed": ["公开真相优先于关系安全"],
    },
    "ending_bury": {
        "protected": ["林与材料中的私人生活"],
        "harmed": ["受害者与公众的知情机会"],
        "believed": ["先保护具体的人"],
    },
    "ending_confront": {
        "protected": ["尚未公开的完整证据链"],
        "harmed": ["陈警官与你的行动安全"],
        "believed": ["先逼当事人承担解释责任"],
    },
}


PROFILE_ECHOES = [
    {
        "id": "profile_truth_first",
        "label": "真相优先",
        "text": "你把公开真相放在了关系安全之前。",
        "requirements": [{"state": "stance.truth_first", "min": 1}],
    },
    {
        "id": "profile_protect_person",
        "label": "保护具体的人",
        "text": "你倾向先保护具体的人，再处理真相的代价。",
        "requirements": [{"state": "stance.protect_person", "min": 1}],
    },
    {
        "id": "profile_chen_trust",
        "label": "陈的信任",
        "text": "陈警官更愿意把你当成合作者。",
        "requirements": [{"state": "relationships.chen.trust", "min": 2}],
    },
    {
        "id": "profile_chen_suspicion",
        "label": "陈的怀疑",
        "text": "陈警官已经开始怀疑你掌握了不该掌握的东西。",
        "requirements": [{"state": "relationships.chen.suspicion", "min": 2}],
    },
    {
        "id": "profile_lin_bond",
        "label": "与林的关联",
        "text": "你和林的关联变强，结局更难把她当成单纯线索。",
        "requirements": [{"state": "relationships.lin.bond", "min": 2}],
    },
    {
        "id": "profile_company_alert",
        "label": "公司警觉",
        "text": "公司侧的警觉升高，后续行动会更难隐藏。",
        "requirements": [{"state": "pressure.company_alert", "min": 2}],
    },
]


def convert_v0_game(v0_game: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    ending_ids = {ending["id"] for ending in v0_game.get("endings", [])}
    chapter_ids: dict[str, str] = {}
    for scene in v0_game.get("scenes", []):
        chapter = scene["chapter"]
        chapter_ids.setdefault(chapter, f"ch{len(chapter_ids) + 1:02d}")

    game = {
        "schema_version": GAME_SCHEMA_VERSION,
        "entry_scene_id": v0_game["start_scene_id"],
        "scenes": [convert_scene(scene, chapter_ids[scene["chapter"]], ending_ids) for scene in v0_game["scenes"]],
        "endings": [convert_ending(ending) for ending in v0_game["endings"]],
        "profile_echoes": deepcopy(PROFILE_ECHOES),
        "extensions": {
            "investigation": {
                "chapters": [{"id": chapter_id, "title": title} for title, chapter_id in chapter_ids.items()],
                "guidance_policy": "diegetic_once",
                "path_review": True,
            }
        },
    }

    reads, writes = collect_state_usage(game)
    retained_states = reads & writes
    remove_unconsumed_state_writes(game, retained_states)
    reads, writes = collect_state_usage(game)
    retained_states = reads | writes

    registry_states = []
    for key in sorted(retained_states):
        initial = v0_game.get("initial_state", {}).get(key)
        registry_states.append(
            {
                "key": key,
                "family": state_family(key),
                "type": scalar_type(initial),
                "initial": initial,
                "label": STATE_LABELS.get(key, key),
                "purpose": "供行动条件或叙事回声读取，并由玩家观察或行动写入。",
            }
        )
    registry = {"schema_version": STATE_SCHEMA_VERSION, "states": registry_states}
    return game, registry


def convert_scene(scene: dict[str, Any], chapter_id: str, ending_ids: set[str]) -> dict[str, Any]:
    surfaces = [convert_background_block(block) for block in scene.get("background_blocks", [])]
    actions = [convert_action(choice, ending_ids) for choice in scene.get("choices", [])]
    return {
        "id": scene["id"],
        "surfaces": surfaces,
        "actions": actions,
        "echoes": [convert_echo(echo) for echo in scene.get("state_echoes", [])],
        "extensions": {
            "investigation": {
                "chapter_id": chapter_id,
                "chapter_title": scene["chapter"],
                "title": scene["title"],
                "task": scene["task"],
                "pressure": scene["pressure"],
                "main_scene": bool(scene.get("required_for_demo", True)),
            }
        },
    }


def convert_background_block(block: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": block["id"].replace("bg_", "surface_", 1),
        "type": "text",
        "content": {"text": block["text"]},
        "anchors": [convert_anchor(anchor) for anchor in block.get("observe_anchors", [])],
        "extensions": {},
    }


def convert_anchor(anchor: dict[str, Any]) -> dict[str, Any]:
    converted = {
        "id": anchor["id"],
        "label": anchor["label"],
        "discoverability": anchor["discoverability"],
        "locator": {"kind": "text", "exact": anchor["text_range"], "occurrence": 1},
        "effects": deepcopy(anchor.get("effects", [])),
        "unlocks_actions": list(anchor.get("unlocks_choices", [])),
        "fragment": convert_fragment(anchor["opens_fragment"]),
        "extensions": {},
    }
    if anchor.get("guidance"):
        converted["guidance"] = deepcopy(anchor["guidance"])
    if anchor.get("unlock_guidance"):
        converted["unlock_guidance"] = deepcopy(anchor["unlock_guidance"])
    return converted


def convert_fragment(fragment: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": fragment["id"],
        "title": fragment["title"],
        "surfaces": [
            {
                "id": f"surface_{fragment['id']}",
                "type": "text",
                "content": {"text": fragment["body"]},
                "anchors": [convert_anchor(anchor) for anchor in fragment.get("nested_anchors", [])],
                "extensions": {},
            }
        ],
        "evidence_tags": list(fragment.get("evidence_tags", [])),
        "extensions": {},
    }


def convert_action(choice: dict[str, Any], ending_ids: set[str]) -> dict[str, Any]:
    target_id = choice["next_scene"]
    return {
        "id": choice["id"],
        "label": choice["label"],
        "consequence_hint": choice["description"],
        "requirements": deepcopy(choice.get("requirements", [])),
        "effects": deepcopy(choice.get("effects", [])),
        "target": {"type": "ending" if target_id in ending_ids else "scene", "id": target_id},
        "irreversible": bool(choice["irreversible"]),
        "consequence_level": choice["consequence_level"],
        "outcome": choice["outcome"],
        "extensions": {"investigation": {"kind": infer_action_kind(choice)}},
    }


def convert_echo(echo: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": echo["id"],
        "label": echo["label"],
        "text": echo["text"],
        "requirements": deepcopy(echo.get("requirements", [])),
    }


def convert_ending(ending: dict[str, Any]) -> dict[str, Any]:
    portrait = ENDING_PORTRAITS.get(
        ending["id"],
        {
            "protected": ["作品声明的保护对象"],
            "harmed": ["作品声明的受损对象"],
            "believed": ["作品声明的信念"],
        },
    )
    return {
        "id": ending["id"],
        "title": ending["title"],
        "body": ending["body"],
        "tags": list(ending["tags"]),
        "portrait": deepcopy(portrait),
        "extensions": {},
    }


def infer_action_kind(choice: dict[str, Any]) -> str:
    text = f"{choice.get('label', '')} {choice.get('description', '')}"
    if any(token in text for token in ("质问", "对质", "摊牌")):
        return "confront"
    if any(token in text for token in ("等待", "暂不", "不回复", "留在")):
        return "wait"
    if any(token in text for token in ("公开", "发送", "交给", "告诉")):
        return "reveal"
    if any(token in text for token in ("隐藏", "保存", "保护", "隔离", "销毁", "删除")):
        return "conceal"
    if any(token in text for token in ("信任", "联系", "警告", "接受")):
        return "trust"
    if any(token in text for token in ("出卖", "泄露", "背叛")):
        return "betray"
    return "investigate"


def collect_state_usage(game: dict[str, Any]) -> tuple[set[str], set[str]]:
    reads: set[str] = set()
    writes: set[str] = set()
    for scene in game.get("scenes", []):
        for echo in scene.get("echoes", []):
            collect_requirements(echo.get("requirements", []), reads)
        for action in scene.get("actions", []):
            collect_requirements(action.get("requirements", []), reads)
            collect_effects(action.get("effects", []), writes)
        for surface in scene.get("surfaces", []):
            collect_surface_usage(surface, writes)
    for echo in game.get("profile_echoes", []):
        collect_requirements(echo.get("requirements", []), reads)
    return reads, writes


def collect_surface_usage(surface: dict[str, Any], writes: set[str]) -> None:
    for anchor in surface.get("anchors", []):
        collect_effects(anchor.get("effects", []), writes)
        for child_surface in anchor.get("fragment", {}).get("surfaces", []):
            collect_surface_usage(child_surface, writes)


def collect_requirements(requirements: list[dict[str, Any]], output: set[str]) -> None:
    for requirement in requirements:
        if requirement.get("state"):
            output.add(requirement["state"])


def collect_effects(effects: list[dict[str, Any]], output: set[str]) -> None:
    for effect in effects:
        output.update(effect.get("set", {}))
        output.update(effect.get("add", {}))


def remove_unconsumed_state_writes(game: dict[str, Any], retained_states: set[str]) -> None:
    for scene in game.get("scenes", []):
        for action in scene.get("actions", []):
            action["effects"] = filter_effects(action.get("effects", []), retained_states)
        for surface in scene.get("surfaces", []):
            filter_surface_effects(surface, retained_states)


def filter_surface_effects(surface: dict[str, Any], retained_states: set[str]) -> None:
    for anchor in surface.get("anchors", []):
        anchor["effects"] = filter_effects(anchor.get("effects", []), retained_states)
        for child_surface in anchor.get("fragment", {}).get("surfaces", []):
            filter_surface_effects(child_surface, retained_states)


def filter_effects(effects: list[dict[str, Any]], retained_states: set[str]) -> list[dict[str, Any]]:
    filtered: list[dict[str, Any]] = []
    for effect in effects:
        operation = "set" if "set" in effect else "add" if "add" in effect else ""
        if not operation:
            continue
        values = {key: value for key, value in effect[operation].items() if key in retained_states}
        if values:
            filtered.append({operation: values})
    return filtered


def state_family(key: str) -> str:
    prefix = key.split(".", 1)[0]
    return {
        "clues": "clue",
        "stance": "stance",
        "relationships": "relationship",
        "pressure": "pressure",
    }.get(prefix, prefix)


def scalar_type(value: Any) -> str:
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)):
        return "number"
    return "string"


def build_pack_manifest(
    v0_game: dict[str, Any],
    *,
    loop_package: dict[str, Any] | None = None,
    pack_version: str = "1.0.0",
    authorship: str = "agent_assisted",
) -> dict[str, Any]:
    loop = loop_package or {
        "id": "investigation",
        "version": "1.0.0",
        "tier": "verified",
        "verification_status": "debt",
    }
    return {
        "schema_version": PACK_SCHEMA_VERSION,
        "pack_id": v0_game["project"]["id"],
        "title": v0_game["project"]["title"],
        "version": pack_version,
        "kernel_version": KERNEL_VERSION,
        "loop_package": deepcopy(loop),
        "surfaces_used": ["text"],
        "runtime_compat": "^1.0.0",
        "authorship": authorship,
        "experimental_notice": loop.get("tier") == "experimental",
        "entrypoints": {
            "game": "game.json",
            "state_registry": "state_registry.json",
            "provenance": "provenance/manifest.json",
        },
        "extensions": {"investigation": {"source_prd": "PRD_V0"}},
    }


def export_v1_content_pack(
    v0_game: dict[str, Any],
    out_dir: str | Path,
    *,
    loop_package: dict[str, Any] | None = None,
    pack_version: str = "1.0.0",
    authorship: str = "agent_assisted",
    extra_provenance_paths: list[str] | None = None,
    trace_event: str = "migrated_v0_content",
) -> None:
    output = Path(out_dir)
    provenance_dir = output / "provenance"
    assets_dir = output / "assets"
    output.mkdir(parents=True, exist_ok=True)
    provenance_dir.mkdir(parents=True, exist_ok=True)
    assets_dir.mkdir(parents=True, exist_ok=True)

    game, registry = convert_v0_game(v0_game)
    write_json(output / "game.json", game)
    write_json(output / "state_registry.json", registry)

    generation = v0_game.get("generation", {})
    trace = {
        "trace_schema_version": "narrative_generation_trace_v1",
        "event": trace_event,
        "source_schema": v0_game.get("schema_version", "unknown"),
        "provider": generation.get("provider", "offline"),
        "model": generation.get("model", "unknown"),
        "prompt_set": active_prompt_set_id(),
        "kernel_version": KERNEL_VERSION,
    }
    trace_path = provenance_dir / "generation_trace.jsonl"
    trace_path.write_text(json.dumps(trace, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")

    provenance = {
        "schema_version": PROVENANCE_SCHEMA_VERSION,
        "authorship": authorship,
        "prompt_set": active_prompt_set_id(),
        "provider": generation.get("provider", "offline"),
        "model": generation.get("model", "unknown"),
        "schema_versions": {
            "kernel": KERNEL_VERSION,
            "game": GAME_SCHEMA_VERSION,
            "state": STATE_SCHEMA_VERSION,
        },
        "trace_version": "narrative_generation_trace_v1",
        "artifacts": [
            {"path": "game.json", "sha256": file_digest(output / "game.json")},
            {"path": "state_registry.json", "sha256": file_digest(output / "state_registry.json")},
            {"path": "provenance/generation_trace.jsonl", "sha256": file_digest(trace_path)},
        ],
    }
    for relative in extra_provenance_paths or []:
        path = output / relative
        provenance["artifacts"].append({"path": relative, "sha256": file_digest(path)})
    write_json(provenance_dir / "manifest.json", provenance)
    write_json(
        output / "pack.json",
        build_pack_manifest(
            v0_game,
            loop_package=loop_package,
            pack_version=pack_version,
            authorship=authorship,
        ),
    )


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=False) + "\n", encoding="utf-8")
