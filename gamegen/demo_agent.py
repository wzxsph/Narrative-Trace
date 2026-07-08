from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from .llm_client import LLMClient, LLMConfig
from .validator import build_path_map, validate_game, write_validation_report


def load_brief(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def generate_game(brief: dict[str, Any], provider: str = "auto") -> dict[str, Any]:
    game = deterministic_demo_game(brief)
    if provider in {"auto", "llm"}:
        config = LLMConfig.from_env()
        if config:
            client = LLMClient(config)
            try:
                apply_llm_polish(game, brief, client)
                game.setdefault("generation", {})["provider"] = "openai_compatible"
            except Exception as exc:  # noqa: BLE001 - keep demo generation resilient
                game.setdefault("generation", {})["provider"] = "offline_fallback"
                game.setdefault("generation", {})["llm_error"] = str(exc)
        elif provider == "llm":
            raise RuntimeError("LLM provider requested, but LLM_BASE_URL or LLM_API_KEY is missing")
        else:
            game.setdefault("generation", {})["provider"] = "offline"
    else:
        game.setdefault("generation", {})["provider"] = "offline"
    return game


def apply_llm_polish(game: dict[str, Any], brief: dict[str, Any], client: LLMClient) -> None:
    """Optional small-scope LLM pass. Structure remains deterministic."""
    system_prompt = (
        "You are polishing one vertical mobile text adventure scene. "
        "Return JSON only. Do not change IDs, structure, choices, or state keys."
    )
    first_scene = game["scenes"][0]
    user_prompt = json.dumps(
        {
            "task": "Rewrite the first background block in concise Chinese while preserving all anchor substrings exactly.",
            "theme_question": brief["project"]["theme_question"],
            "required_anchor_substrings": [
                anchor["text_range"] for anchor in first_scene["background_blocks"][0]["observe_anchors"]
            ],
            "current_text": first_scene["background_blocks"][0]["text"],
            "return_shape": {"text": "string"},
        },
        ensure_ascii=False,
    )
    result = client.complete_json(system_prompt, user_prompt)
    text = result.get("text")
    if isinstance(text, str) and all(
        anchor["text_range"] in text for anchor in first_scene["background_blocks"][0]["observe_anchors"]
    ):
        first_scene["background_blocks"][0]["text"] = text


def deterministic_demo_game(brief: dict[str, Any]) -> dict[str, Any]:
    project = brief["project"]
    return {
        "schema_version": "game_writer_demo_v0",
        "project": {
            "id": project["id"],
            "title": project["title"],
            "theme_question": project["theme_question"],
            "interface": brief["world"]["interface"],
        },
        "start_scene_id": "ch01_phone_lock",
        "initial_state": {
            "clues.station_location": False,
            "clues.chen_trimmed_location": False,
            "clues.backup_copy": False,
            "clues.lin_confession": False,
            "stance.truth_first": 0,
            "stance.protect_person": 0,
            "relationships.chen.trust": 0,
            "relationships.chen.suspicion": 0,
            "relationships.lin.bond": 0,
            "pressure.company_alert": 0,
        },
        "scenes": [
            scene_phone_lock(),
            scene_station(),
            scene_backup(),
        ],
        "endings": [
            {
                "id": "ending_publish",
                "title": "公开的真相",
                "body": "你把副本交给了媒体。林得救了，但陈警官的名字也被卷进风暴。城市知道了真相，却没人能轻松地说自己完全无辜。",
                "tags": ["truth_first", "lin_survived", "chen_exposed"],
            },
            {
                "id": "ending_bury",
                "title": "沉默的备份",
                "body": "你保存了证据，却没有公开。手机被清除后，世界恢复了安静。只有你知道，那份安静是用谁的秘密换来的。",
                "tags": ["protect_person", "truth_buried", "private_archive"],
            },
            {
                "id": "ending_confront",
                "title": "被迫摊牌",
                "body": "你带着截断记录质问陈。谈话被公司远程会话捕获，所有人都失去了退路。真相比你预想得更快抵达，也更粗暴。",
                "tags": ["chen_suspicious", "company_alerted", "unstable_truth"],
            },
        ],
    }


def scene_phone_lock() -> dict[str, Any]:
    return {
        "id": "ch01_phone_lock",
        "chapter": "第一章：锁屏上的半句话",
        "title": "锁屏上的半句话",
        "task": "在远程清除前确认林最后联系的人。",
        "pressure": "远程清除 06:00",
        "required_for_demo": True,
        "background_blocks": [
            {
                "id": "bg_lock_01",
                "text": "手机亮起。未发送短信停在输入框里：“如果我没回来，不要相信陈...” 顶部通知显示：远程清除已排队。锁屏时间停在 02:13。",
                "observe_anchors": [
                    {
                        "id": "obs_unsent_sms",
                        "text_range": "未发送短信",
                        "label": "查看短信草稿",
                        "discoverability": "obvious",
                        "depth": 1,
                        "effects": [{"set": {"clues.unsent_warning": True}}],
                        "unlocks_choices": [],
                        "opens_fragment": {
                            "id": "frag_unsent_sms",
                            "title": "未发送的短信",
                            "body": "草稿创建于 02:13，最后一次编辑停在“陈”字后。输入法候选里，第一个词是“陈警官”，第二个词是“陈述”。",
                            "evidence_tags": ["warning", "chen"],
                            "nested_anchors": [
                                {
                                    "id": "obs_0213_log",
                                    "text_range": "02:13",
                                    "label": "对照系统日志",
                                    "discoverability": "subtle",
                                    "depth": 2,
                                    "effects": [{"set": {"clues.station_location": True}}],
                                    "unlocks_choices": ["choice_go_station"],
                                    "opens_fragment": {
                                        "id": "frag_0213_log",
                                        "title": "02:13 的系统日志",
                                        "body": "02:13 时手机短暂开启定位，地点是城北废弃地铁站。4 秒后，定位记录被手动截断。",
                                        "evidence_tags": ["location", "station"],
                                        "nested_anchors": [
                                            {
                                                "id": "obs_trimmed_gap",
                                                "text_range": "手动截断",
                                                "label": "检查截断痕迹",
                                                "discoverability": "subtle",
                                                "depth": 3,
                                                "effects": [{"set": {"clues.chen_trimmed_location": True}}],
                                                "unlocks_choices": ["choice_confront_chen"],
                                                "opens_fragment": {
                                                    "id": "frag_trimmed_gap",
                                                    "title": "被截断的 4 秒",
                                                    "body": "截断命令来自一个备注为“陈”的联系人号码。这不是系统自动清理。",
                                                    "evidence_tags": ["chen", "tamper"],
                                                    "nested_anchors": [],
                                                },
                                            }
                                        ],
                                    },
                                }
                            ],
                        },
                    },
                    {
                        "id": "obs_remote_wipe",
                        "text_range": "远程清除",
                        "label": "查看远程清除来源",
                        "discoverability": "obvious",
                        "depth": 1,
                        "effects": [{"add": {"pressure.company_alert": 1}}],
                        "unlocks_choices": ["choice_delay_wipe"],
                        "opens_fragment": {
                            "id": "frag_remote_wipe",
                            "title": "远程清除队列",
                            "body": "清除请求不是来自普通云服务，而是来自林调查过的公司设备管理后台。队列里有一个临时的暂停窗口。",
                            "evidence_tags": ["pressure", "company"],
                            "nested_anchors": [
                                {
                                    "id": "obs_pause_window",
                                    "text_range": "暂停窗口",
                                    "label": "检查暂停窗口",
                                    "discoverability": "subtle",
                                    "depth": 2,
                                    "effects": [{"set": {"clues.wipe_pause_window": True}}],
                                    "unlocks_choices": ["choice_delay_wipe"],
                                    "opens_fragment": {
                                        "id": "frag_pause_window",
                                        "title": "六分钟暂停窗口",
                                        "body": "你可以让清除队列延迟六分钟，但系统会记录这次入侵。",
                                        "evidence_tags": ["timer"],
                                        "nested_anchors": [],
                                    },
                                }
                            ],
                        },
                    },
                    {
                        "id": "obs_time_0213",
                        "text_range": "02:13",
                        "label": "查看锁屏时间",
                        "discoverability": "subtle",
                        "depth": 1,
                        "effects": [{"set": {"clues.lock_time_0213": True}}],
                        "unlocks_choices": [],
                        "opens_fragment": {
                            "id": "frag_time_0213",
                            "title": "停住的时间",
                            "body": "02:13 同时出现在短信草稿、定位日志和锁屏时间里。林像是故意把这个时间留给你。",
                            "evidence_tags": ["pattern"],
                            "nested_anchors": [],
                        },
                    },
                ],
            }
        ],
        "choices": [
            {
                "id": "choice_call_chen",
                "label": "联系陈警官",
                "description": "你会把目前情况告诉他，但短信正在警告你不要相信“陈”。",
                "requirements": [],
                "effects": [{"add": {"relationships.chen.trust": 1}}],
                "next_scene": "ch02_station",
                "irreversible": True,
                "consequence_level": "chapter",
                "outcome": "陈接得很快。他听完后只问了一句：“你看过里面的内容了吗？”",
            },
            {
                "id": "choice_go_station",
                "label": "前往废弃地铁站",
                "description": "你会离开安全地点，手机可能在路上被清除。",
                "requirements": [{"state": "clues.station_location", "equals": True}],
                "effects": [{"add": {"stance.truth_first": 1}}],
                "next_scene": "ch02_station",
                "irreversible": True,
                "consequence_level": "global",
                "outcome": "你把手机揣进口袋。导航路线亮起，终点是城北废弃地铁站。",
            },
            {
                "id": "choice_delay_wipe",
                "label": "延迟远程清除",
                "description": "你会保住手机内容，也会留下入侵记录。",
                "requirements": [{"state": "clues.wipe_pause_window", "equals": True}],
                "effects": [{"add": {"pressure.company_alert": 1}}],
                "next_scene": "ch02_station",
                "irreversible": True,
                "consequence_level": "global",
                "outcome": "倒计时跳回 12:00。屏幕角落多了一个你没见过的远程会话图标。",
            },
            {
                "id": "choice_confront_chen",
                "label": "带着截断记录质问陈",
                "description": "你掌握了他改动定位的痕迹，但摊牌会让他知道你已经查到这里。",
                "requirements": [{"state": "clues.chen_trimmed_location", "equals": True}],
                "effects": [{"add": {"relationships.chen.suspicion": 2}}, {"add": {"pressure.company_alert": 1}}],
                "next_scene": "ch03_backup",
                "irreversible": True,
                "consequence_level": "global",
                "outcome": "陈沉默了三秒：“你不该看到那四秒。”",
            },
        ],
    }


def scene_station() -> dict[str, Any]:
    return {
        "id": "ch02_station",
        "chapter": "第二章：废弃地铁站",
        "title": "废弃地铁站",
        "task": "确认林在地铁站留下了什么。",
        "pressure": "公司警报升高",
        "required_for_demo": True,
        "background_blocks": [
            {
                "id": "bg_station_01",
                "text": "站台没有灯，只有手机屏幕照亮墙上的旧广告。广告背面贴着一张车票，票根上写着“别公开录音”。轨道旁的储物柜还亮着微弱红点。",
                "observe_anchors": [
                    {
                        "id": "obs_ticket",
                        "text_range": "车票",
                        "label": "取下车票",
                        "discoverability": "obvious",
                        "depth": 1,
                        "effects": [{"set": {"clues.ticket_warning": True}}],
                        "unlocks_choices": [],
                        "opens_fragment": {
                            "id": "frag_ticket",
                            "title": "一张旧车票",
                            "body": "车票背面写着：录音是真的，剪辑是假的。底部还有一串储物柜编号：A-17。",
                            "evidence_tags": ["recording", "locker"],
                            "nested_anchors": [
                                {
                                    "id": "obs_locker_code",
                                    "text_range": "A-17",
                                    "label": "核对储物柜编号",
                                    "discoverability": "subtle",
                                    "depth": 2,
                                    "effects": [{"set": {"clues.locker_a17": True}}],
                                    "unlocks_choices": ["choice_open_locker"],
                                    "opens_fragment": {
                                        "id": "frag_locker_code",
                                        "title": "A-17",
                                        "body": "A-17 的柜门没有锁死，只要用手机靠近就能触发离线备份。",
                                        "evidence_tags": ["backup"],
                                        "nested_anchors": [],
                                    },
                                }
                            ],
                        },
                    },
                    {
                        "id": "obs_red_dot",
                        "text_range": "微弱红点",
                        "label": "检查红点",
                        "discoverability": "subtle",
                        "depth": 1,
                        "effects": [{"set": {"clues.hidden_camera": True}}],
                        "unlocks_choices": ["choice_cover_camera"],
                        "opens_fragment": {
                            "id": "frag_red_dot",
                            "title": "隐藏摄像头",
                            "body": "红点来自一个临时摄像头。它正在上传低清画面，上传目的地仍是那套公司后台。",
                            "evidence_tags": ["camera", "company"],
                            "nested_anchors": [],
                        },
                    },
                    {
                        "id": "obs_recording_warning",
                        "text_range": "别公开录音",
                        "label": "辨认字迹",
                        "discoverability": "obvious",
                        "depth": 1,
                        "effects": [{"set": {"clues.lin_confession": True}}],
                        "unlocks_choices": ["choice_protect_lin"],
                        "opens_fragment": {
                            "id": "frag_recording_warning",
                            "title": "林的字迹",
                            "body": "这是林的字。她不是说录音不存在，而是在求你不要公开它。",
                            "evidence_tags": ["lin", "moral_pressure"],
                            "nested_anchors": [],
                        },
                    },
                ],
            }
        ],
        "choices": [
            {
                "id": "choice_wait_station",
                "label": "继续等待",
                "description": "你会错过清除前的窗口，但可能看清是谁在监视这里。",
                "requirements": [],
                "effects": [{"add": {"pressure.company_alert": 1}}],
                "next_scene": "ch03_backup",
                "irreversible": True,
                "consequence_level": "chapter",
                "outcome": "五分钟后，摄像头自动转向了你。你等到了答案，也暴露了自己。",
            },
            {
                "id": "choice_open_locker",
                "label": "打开 A-17 储物柜",
                "description": "你会取得备份，也会触发林留下的最后留言。",
                "requirements": [{"state": "clues.locker_a17", "equals": True}],
                "effects": [{"set": {"clues.backup_copy": True}}, {"add": {"relationships.lin.bond": 1}}],
                "next_scene": "ch03_backup",
                "irreversible": True,
                "consequence_level": "global",
                "outcome": "柜门弹开，手机自动接收一份加密副本。林的留言开始播放。",
            },
            {
                "id": "choice_cover_camera",
                "label": "遮住隐藏摄像头",
                "description": "你能争取一点安全时间，但公司会知道有人发现了监控。",
                "requirements": [{"state": "clues.hidden_camera", "equals": True}],
                "effects": [{"add": {"pressure.company_alert": 1}}],
                "next_scene": "ch03_backup",
                "irreversible": True,
                "consequence_level": "chapter",
                "outcome": "画面中断。几乎同时，手机收到一条没有号码的短信：别再碰柜子。",
            },
            {
                "id": "choice_protect_lin",
                "label": "先保护林的秘密",
                "description": "你会暂时不碰录音，但真相可能因此被永远藏住。",
                "requirements": [{"state": "clues.lin_confession", "equals": True}],
                "effects": [{"add": {"stance.protect_person": 1}}],
                "next_scene": "ch03_backup",
                "irreversible": True,
                "consequence_level": "ending",
                "outcome": "你把车票折好收进口袋。手机屏幕暗下去，像是林终于短暂地信了你一次。",
            },
        ],
    }


def scene_backup() -> dict[str, Any]:
    return {
        "id": "ch03_backup",
        "chapter": "第三章：被保存的副本",
        "title": "被保存的副本",
        "task": "决定是否公开林留下的备份。",
        "pressure": "最后选择",
        "required_for_demo": True,
        "background_blocks": [
            {
                "id": "bg_backup_01",
                "text": "备份解密完成。屏幕上有两份文件：原始录音和剪辑版本。林的最后留言写着：“真相不是没有代价，只是代价别让无辜的人替我付。”",
                "observe_anchors": [
                    {
                        "id": "obs_raw_recording",
                        "text_range": "原始录音",
                        "label": "播放原始录音",
                        "discoverability": "obvious",
                        "depth": 1,
                        "effects": [{"set": {"clues.raw_recording": True}}],
                        "unlocks_choices": ["choice_publish_truth"],
                        "opens_fragment": {
                            "id": "frag_raw_recording",
                            "title": "原始录音",
                            "body": "原始录音能证明公司伪造证据，但也会暴露林曾经剪辑过另一段证词。",
                            "evidence_tags": ["truth", "cost"],
                            "nested_anchors": [],
                        },
                    },
                    {
                        "id": "obs_edited_recording",
                        "text_range": "剪辑版本",
                        "label": "比对剪辑版本",
                        "discoverability": "subtle",
                        "depth": 1,
                        "effects": [{"set": {"clues.edited_recording": True}}],
                        "unlocks_choices": ["choice_confront_final"],
                        "opens_fragment": {
                            "id": "frag_edited_recording",
                            "title": "剪辑版本",
                            "body": "剪辑版本删去了陈警官阻止上报的两句话，也删去了林承认自己曾经越界的一句。",
                            "evidence_tags": ["chen", "lin"],
                            "nested_anchors": [],
                        },
                    },
                    {
                        "id": "obs_final_message",
                        "text_range": "最后留言",
                        "label": "阅读最后留言",
                        "discoverability": "obvious",
                        "depth": 1,
                        "effects": [{"set": {"clues.final_message": True}}],
                        "unlocks_choices": ["choice_keep_archive"],
                        "opens_fragment": {
                            "id": "frag_final_message",
                            "title": "林的最后留言",
                            "body": "她没有请求你救她。她只请求你在公开之前，先想清楚谁会因此被毁掉。",
                            "evidence_tags": ["moral_pressure"],
                            "nested_anchors": [],
                        },
                    },
                ],
            }
        ],
        "choices": [
            {
                "id": "choice_publish_truth",
                "label": "公开原始录音",
                "description": "公司会被迫回应，林的污点也会一起暴露。",
                "requirements": [{"state": "clues.raw_recording", "equals": True}],
                "effects": [{"add": {"stance.truth_first": 2}}],
                "next_scene": "ending_publish",
                "irreversible": True,
                "consequence_level": "ending",
                "outcome": "你按下发布。上传条走到尽头时，手机终于被远程清除。",
            },
            {
                "id": "choice_keep_archive",
                "label": "保存但暂不公开",
                "description": "你保住证据，也选择暂时替所有人守住秘密。",
                "requirements": [{"state": "clues.final_message", "equals": True}],
                "effects": [{"add": {"stance.protect_person": 2}}],
                "next_scene": "ending_bury",
                "irreversible": True,
                "consequence_level": "ending",
                "outcome": "你把副本转入离线存储。屏幕黑掉之前，最后一条日志显示：清除完成。",
            },
            {
                "id": "choice_confront_final",
                "label": "把剪辑痕迹发给陈",
                "description": "你逼他解释那两句话，但公司可能正在监听。",
                "requirements": [{"state": "clues.edited_recording", "equals": True}],
                "effects": [{"add": {"relationships.chen.suspicion": 1}}, {"add": {"pressure.company_alert": 1}}],
                "next_scene": "ending_confront",
                "irreversible": True,
                "consequence_level": "ending",
                "outcome": "陈只回了四个字：现在别发。下一秒，远程会话接管了屏幕。",
            },
        ],
    }


def export_game(game: dict[str, Any], out_dir: str | Path) -> None:
    output = Path(out_dir)
    output.mkdir(parents=True, exist_ok=True)
    (output / "game.json").write_text(json.dumps(game, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output / "game.yaml").write_text(to_yaml_like(game), encoding="utf-8")
    path_map = build_path_map(game)
    (output / "path_map.json").write_text(json.dumps(path_map, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    state_registry = build_state_registry(game)
    (output / "state_registry.json").write_text(
        json.dumps(state_registry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    messages = validate_game(game)
    write_validation_report(messages, output / "validation_report.md")
    trace = {
        "provider": game.get("generation", {}).get("provider", "offline"),
        "artifacts": ["game.json", "game.yaml", "path_map.json", "state_registry.json", "validation_report.md"],
    }
    (output / "generation_trace.jsonl").write_text(json.dumps(trace, ensure_ascii=False) + "\n", encoding="utf-8")


def build_state_registry(game: dict[str, Any]) -> dict[str, Any]:
    registry: dict[str, dict[str, list[str]]] = {}

    def ensure(ref: str) -> dict[str, list[str]]:
        return registry.setdefault(ref, {"writes": [], "reads": []})

    for scene in game["scenes"]:
        scene_id = scene["id"]
        for choice in scene.get("choices", []):
            for requirement in choice.get("requirements", []):
                if requirement.get("state"):
                    ensure(requirement["state"])["reads"].append(f"{scene_id}.{choice['id']}.requirements")
            for effect in choice.get("effects", []):
                for ref in effect.get("set", {}).keys():
                    ensure(ref)["writes"].append(f"{scene_id}.{choice['id']}.effects")
                for ref in effect.get("add", {}).keys():
                    ensure(ref)["writes"].append(f"{scene_id}.{choice['id']}.effects")
        for block in scene.get("background_blocks", []):
            for anchor in block.get("observe_anchors", []):
                collect_anchor_state(anchor, scene_id, ensure)
    return {"states": registry}


def collect_anchor_state(anchor: dict[str, Any], scene_id: str, ensure) -> None:
    for effect in anchor.get("effects", []):
        for ref in effect.get("set", {}).keys():
            ensure(ref)["writes"].append(f"{scene_id}.{anchor['id']}.effects")
        for ref in effect.get("add", {}).keys():
            ensure(ref)["writes"].append(f"{scene_id}.{anchor['id']}.effects")
    for child in anchor.get("opens_fragment", {}).get("nested_anchors", []):
        collect_anchor_state(child, scene_id, ensure)


def to_yaml_like(value: Any, indent: int = 0) -> str:
    space = "  " * indent
    if isinstance(value, dict):
        lines: list[str] = []
        for key, item in value.items():
            if isinstance(item, (dict, list)):
                lines.append(f"{space}{key}:")
                lines.append(to_yaml_like(item, indent + 1).rstrip())
            else:
                lines.append(f"{space}{key}: {json.dumps(item, ensure_ascii=False)}")
        return "\n".join(lines) + "\n"
    if isinstance(value, list):
        lines = []
        for item in value:
            if isinstance(item, (dict, list)):
                rendered = to_yaml_like(item, indent + 1).rstrip().splitlines()
                lines.append(f"{space}- {rendered[0].lstrip()}")
                lines.extend(rendered[1:])
            else:
                lines.append(f"{space}- {json.dumps(item, ensure_ascii=False)}")
        return "\n".join(lines) + "\n"
    return f"{space}{json.dumps(value, ensure_ascii=False)}\n"

