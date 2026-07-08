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
        "schema_version": "game_writer_demo_v0_3",
        "project": {
            "id": project["id"],
            "title": project["title"],
            "theme_question": project["theme_question"],
            "interface": brief["world"]["interface"],
        },
        "start_scene_id": "ch01_phone_lock",
        "initial_state": {
            "clues.unsent_warning": False,
            "clues.station_location": False,
            "clues.chen_trimmed_location": False,
            "clues.wipe_pause_window": False,
            "clues.lock_time_0213": False,
            "clues.cloud_admin": False,
            "clues.freeze_token": False,
            "clues.screen_recording": False,
            "clues.chen_alias": False,
            "clues.chen_casefile": False,
            "clues.station_route_confirmed": False,
            "clues.voice_note": False,
            "clues.station_entry_code": False,
            "clues.security_booth": False,
            "clues.camera_blind_spot": False,
            "clues.ticket_warning": False,
            "clues.locker_a17": False,
            "clues.hidden_camera": False,
            "clues.backup_copy": False,
            "clues.lin_audio_key": False,
            "clues.victim_list": False,
            "clues.lin_confession": False,
            "clues.raw_recording": False,
            "clues.edited_recording": False,
            "clues.final_message": False,
            "clues.chen_motive": False,
            "clues.public_packet_ready": False,
            "clues.archive_ready": False,
            "clues.chen_message_ready": False,
            "stance.truth_first": 0,
            "stance.protect_person": 0,
            "relationships.chen.trust": 0,
            "relationships.chen.suspicion": 0,
            "relationships.lin.bond": 0,
            "pressure.company_alert": 0,
        },
        "scenes": [
            scene_phone_lock(),
            scene_cloud_console(),
            scene_contact_trace(),
            scene_station_gate(),
            scene_station_platform(),
            scene_locker_room(),
            scene_backup_unlock(),
            scene_witness_thread(),
            scene_publish_decision(),
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


def make_scene(
    scene_id: str,
    chapter: str,
    title: str,
    task: str,
    pressure: str,
    text: str,
    anchors: list[dict[str, Any]],
    choices: list[dict[str, Any]],
    state_echoes: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "id": scene_id,
        "chapter": chapter,
        "title": title,
        "task": task,
        "pressure": pressure,
        "required_for_demo": True,
        "state_echoes": state_echoes or [],
        "background_blocks": [{"id": f"bg_{scene_id}", "text": text, "observe_anchors": anchors}],
        "choices": choices,
    }


def make_anchor(
    anchor_id: str,
    text_range: str,
    label: str,
    depth: int,
    effects: list[dict[str, Any]],
    unlocks_choices: list[str],
    body: str,
    tags: list[str],
    nested: list[dict[str, Any]] | None = None,
    title: str | None = None,
    discoverability: str = "obvious",
) -> dict[str, Any]:
    return {
        "id": anchor_id,
        "text_range": text_range,
        "label": label,
        "discoverability": discoverability,
        "depth": depth,
        "effects": effects,
        "unlocks_choices": unlocks_choices,
        "opens_fragment": {
            "id": f"frag_{anchor_id.removeprefix('obs_')}",
            "title": title or label,
            "body": body,
            "evidence_tags": tags,
            "nested_anchors": nested or [],
        },
    }


def make_choice(
    choice_id: str,
    label: str,
    description: str,
    next_scene: str,
    outcome: str,
    requirements: list[dict[str, Any]] | None = None,
    effects: list[dict[str, Any]] | None = None,
    consequence_level: str = "chapter",
) -> dict[str, Any]:
    return {
        "id": choice_id,
        "label": label,
        "description": description,
        "requirements": requirements or [],
        "effects": effects or [],
        "next_scene": next_scene,
        "irreversible": True,
        "consequence_level": consequence_level,
        "outcome": outcome,
    }


def make_echo(
    echo_id: str,
    label: str,
    text: str,
    requirements: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "id": echo_id,
        "label": label,
        "text": text,
        "requirements": requirements,
    }


def scene_phone_lock() -> dict[str, Any]:
    return make_scene(
        "ch01_phone_lock",
        "第一章：锁屏上的半句话",
        "锁屏上的半句话",
        "在远程清除前确认林最后联系的人。",
        "远程清除 06:00",
        "手机亮起。未发送短信停在输入框里：“如果我没回来，不要相信陈...” 顶部通知显示：远程清除已排队。锁屏时间停在 02:13。",
        [
            make_anchor(
                "obs_unsent_sms",
                "未发送短信",
                "查看短信草稿",
                1,
                [{"set": {"clues.unsent_warning": True}}],
                [],
                "草稿创建于 02:13，最后一次编辑停在“陈”字后。输入法候选里，第一个词是“陈警官”，第二个词是“陈述”。",
                ["warning", "chen"],
                [
                    make_anchor(
                        "obs_0213_log",
                        "02:13",
                        "对照系统日志",
                        2,
                        [{"set": {"clues.station_location": True}}],
                        ["choice_go_station"],
                        "02:13 时手机短暂开启定位，地点是城北废弃地铁站。4 秒后，定位记录被手动截断。",
                        ["location", "station"],
                        [
                            make_anchor(
                                "obs_trimmed_gap",
                                "手动截断",
                                "检查截断痕迹",
                                3,
                                [{"set": {"clues.chen_trimmed_location": True}}],
                                ["choice_confront_chen"],
                                "截断命令来自一个备注为“陈”的联系人号码。这不是系统自动清理。",
                                ["chen", "tamper"],
                                discoverability="subtle",
                            )
                        ],
                        discoverability="subtle",
                    )
                ],
            ),
            make_anchor(
                "obs_remote_wipe",
                "远程清除",
                "查看远程清除来源",
                1,
                [{"add": {"pressure.company_alert": 1}}],
                ["choice_delay_wipe"],
                "清除请求不是来自普通云服务，而是来自林调查过的公司设备管理后台。队列里有一个临时的暂停窗口。",
                ["pressure", "company"],
                [
                    make_anchor(
                        "obs_pause_window",
                        "暂停窗口",
                        "检查暂停窗口",
                        2,
                        [{"set": {"clues.wipe_pause_window": True}}],
                        ["choice_delay_wipe"],
                        "你可以让清除队列延迟六分钟，但系统会记录这次入侵。",
                        ["timer"],
                        discoverability="subtle",
                    )
                ],
            ),
            make_anchor(
                "obs_time_0213",
                "02:13",
                "查看锁屏时间",
                1,
                [{"set": {"clues.lock_time_0213": True}}],
                [],
                "02:13 同时出现在短信草稿、定位日志和锁屏时间里。林像是故意把这个时间留给你。",
                ["pattern"],
                discoverability="subtle",
            ),
        ],
        [
            make_choice(
                "choice_call_chen",
                "联系陈警官",
                "你会把目前情况告诉他，但短信正在警告你不要相信“陈”。",
                "ch01_cloud_console",
                "陈接得很快。他听完后只问了一句：“你看过里面的内容了吗？”",
                effects=[{"add": {"relationships.chen.trust": 1}}],
            ),
            make_choice(
                "choice_go_station",
                "前往废弃地铁站",
                "你会离开安全地点，但手机要求先处理远程清除。",
                "ch01_cloud_console",
                "你把手机揣进口袋。导航路线亮起，云端控制台却先弹了出来。",
                requirements=[{"state": "clues.station_location", "equals": True}],
                effects=[{"add": {"stance.truth_first": 1}}],
                consequence_level="global",
            ),
            make_choice(
                "choice_delay_wipe",
                "延迟远程清除",
                "你会保住手机内容，也会留下入侵记录。",
                "ch01_cloud_console",
                "倒计时跳回 12:00。屏幕角落多了一个你没见过的远程会话图标。",
                requirements=[{"state": "clues.wipe_pause_window", "equals": True}],
                effects=[{"add": {"pressure.company_alert": 1}}],
                consequence_level="global",
            ),
            make_choice(
                "choice_confront_chen",
                "带着截断记录质问陈",
                "你掌握了他改动定位的痕迹，但摊牌会让他知道你已经查到这里。",
                "ch01_contact_trace",
                "陈沉默了三秒：“你不该看到那四秒。”",
                requirements=[{"state": "clues.chen_trimmed_location", "equals": True}],
                effects=[{"add": {"relationships.chen.suspicion": 2}}, {"add": {"pressure.company_alert": 1}}],
                consequence_level="global",
            ),
        ],
    )


def scene_cloud_console() -> dict[str, Any]:
    return make_scene(
        "ch01_cloud_console",
        "第一章：锁屏上的半句话",
        "云端控制台",
        "阻止手机在路上被清空。",
        "远程会话在线",
        "云端控制台自动展开。设备管理后台列出三台设备，临时令牌只剩一次使用机会，右上角的屏幕录制仍在跳秒。",
        [
            make_anchor(
                "obs_device_admin",
                "设备管理后台",
                "核对后台来源",
                1,
                [{"set": {"clues.cloud_admin": True}}],
                ["choice_isolate_phone"],
                "后台证书属于林调查过的公司。三台设备最近一次登录都不在公司内网，其中一台落在陈警官所在辖区的公共终端。",
                ["company", "chen"],
                [
                    make_anchor(
                        "obs_three_devices",
                        "三台设备",
                        "查看设备列表",
                        2,
                        [{"add": {"pressure.company_alert": 1}}],
                        ["choice_isolate_phone"],
                        "三台设备里只有林的手机仍在移动，另外两台设备像是在给它打掩护。",
                        ["device"],
                        discoverability="subtle",
                    )
                ],
            ),
            make_anchor(
                "obs_session_token",
                "临时令牌",
                "复制临时令牌",
                1,
                [{"set": {"clues.freeze_token": True}}],
                ["choice_freeze_wipe"],
                "令牌可以冻结清除队列，但会把你的设备指纹写入后台日志。",
                ["timer", "risk"],
            ),
            make_anchor(
                "obs_screen_recording",
                "屏幕录制",
                "检查录制来源",
                1,
                [{"set": {"clues.screen_recording": True}}],
                ["choice_blind_recording"],
                "录制窗口没有麦克风权限，只能看见你点了什么，看不见你听见了什么。",
                ["surveillance"],
                discoverability="subtle",
            ),
        ],
        [
            make_choice(
                "choice_freeze_wipe",
                "冻结清除队列",
                "手机内容会暂时安全，但你的指纹会进入公司日志。",
                "ch01_contact_trace",
                "清除队列变成灰色，倒计时旁多了一条新日志：外部令牌介入。",
                requirements=[{"state": "clues.freeze_token", "equals": True}],
                effects=[{"add": {"pressure.company_alert": 1}}],
                consequence_level="global",
            ),
            make_choice(
                "choice_isolate_phone",
                "隔离林的手机",
                "你会切断其他设备掩护，换来一条更干净的追踪路径。",
                "ch01_contact_trace",
                "另外两台设备掉线，林的手机位置被单独标出。",
                requirements=[{"state": "clues.cloud_admin", "equals": True}],
                effects=[{"set": {"clues.station_route_confirmed": True}}],
            ),
            make_choice(
                "choice_blind_recording",
                "遮断屏幕录制",
                "你能隐藏接下来的操作，但会让对方知道你发现了监视。",
                "ch01_contact_trace",
                "录制窗口黑了两秒，又重新亮起。对面一定注意到了。",
                requirements=[{"state": "clues.screen_recording", "equals": True}],
                effects=[{"add": {"pressure.company_alert": 1}}],
            ),
            make_choice(
                "choice_leave_unfrozen",
                "带着倒计时继续查",
                "你不改动后台，换取对方暂时不知道你介入。",
                "ch01_contact_trace",
                "倒计时还在跳。你把手机调成离线，只留下本地日志。",
                effects=[{"add": {"stance.protect_person": 1}}],
            ),
        ],
        state_echoes=[
            make_echo(
                "echo_cloud_chen_call",
                "陈的余音",
                "刚才那通电话还挂在后台记录里。陈没有催你交出手机，只是反复确认你是否还安全。",
                [{"state": "relationships.chen.trust", "min": 1}],
            ),
        ],
    )


def scene_contact_trace() -> dict[str, Any]:
    return make_scene(
        "ch01_contact_trace",
        "第一章：锁屏上的半句话",
        "联系人里的陈",
        "确认陈到底是人名、备注，还是陷阱。",
        "倒计时稳定",
        "联系人陈被置顶在最近通话里。共享案件夹的权限还没关闭，一条出租车订单把林送向城北，语音便签停在未播放状态。",
        [
            make_anchor(
                "obs_chen_alias",
                "联系人陈",
                "核对联系人备注",
                1,
                [{"set": {"clues.chen_alias": True}}],
                [],
                "备注里的陈不只有陈警官，还关联了一个匿名报案人。林把两个号码故意合并在同一张联系人卡里，并把共享案件夹挂在联系人详情下。",
                ["chen", "alias"],
                [
                    make_anchor(
                        "obs_casefile_share",
                        "共享案件夹",
                        "打开共享案件夹",
                        2,
                        [{"set": {"clues.chen_casefile": True}}],
                        ["choice_warn_chen"],
                        "案件夹里有陈警官写给林的草稿：如果录音公开，先保人，再保案子。",
                        ["relationship", "casefile"],
                        discoverability="subtle",
                    )
                ],
            ),
            make_anchor(
                "obs_taxi_order",
                "出租车订单",
                "查看订单路线",
                1,
                [{"set": {"clues.station_route_confirmed": True}}],
                ["choice_leave_for_station"],
                "订单终点不是地铁站正门，而是废弃站旁的旧员工入口。",
                ["location"],
            ),
            make_anchor(
                "obs_voice_note",
                "语音便签",
                "播放语音便签",
                1,
                [{"set": {"clues.voice_note": True}}, {"add": {"relationships.lin.bond": 1}}],
                ["choice_send_voice_to_self"],
                "林的声音很低：别让他们把我变成唯一的坏人。你第一次听见她像是在向你求证，而不是求救。",
                ["lin", "bond"],
            ),
        ],
        [
            make_choice(
                "choice_leave_for_station",
                "沿订单路线去旧员工入口",
                "路线更隐蔽，但会直接进入林最后出现的区域。",
                "ch02_station_gate",
                "你按下确认。第一章的线索收束成一个地点：城北废弃站。",
                requirements=[{"state": "clues.station_route_confirmed", "equals": True}],
                effects=[{"add": {"stance.truth_first": 1}}],
                consequence_level="global",
            ),
            make_choice(
                "choice_send_voice_to_self",
                "备份语音便签",
                "你会保留林的原声，也承担保管她软弱证据的责任。",
                "ch02_station_gate",
                "便签被复制到离线区。林的声音从案件线索变成了一个你必须面对的人。",
                requirements=[{"state": "clues.voice_note", "equals": True}],
                effects=[{"add": {"relationships.lin.bond": 1}}],
                consequence_level="global",
            ),
            make_choice(
                "choice_warn_chen",
                "把共享草稿截图发给陈",
                "他会知道你看见了他的犹豫，也可能因此帮你。",
                "ch02_station_gate",
                "陈回了一个定位点，没有解释，也没有否认。",
                requirements=[{"state": "clues.chen_casefile", "equals": True}],
                effects=[{"add": {"relationships.chen.trust": 1}}],
            ),
            make_choice(
                "choice_follow_old_address",
                "不通知任何人直接出发",
                "你会少暴露一点，但也少一个外部支点。",
                "ch02_station_gate",
                "你锁上屏幕，出租车订单的终点在黑暗里闪了一下。",
                effects=[{"add": {"stance.protect_person": 1}}],
            ),
        ],
        state_echoes=[
            make_echo(
                "echo_contact_chen_trust",
                "陈没有挂断",
                "陈的号码仍停在最近通话第一位。他没有继续追问，像是在给你留下自己判断的空间。",
                [{"state": "relationships.chen.trust", "min": 1}],
            ),
            make_echo(
                "echo_contact_chen_suspicion",
                "陈开始收紧",
                "你质问过那四秒以后，陈的头像旁多了一个未读提示，却没有新消息。他知道你已经越过了安全线。",
                [{"state": "relationships.chen.suspicion", "min": 2}],
            ),
        ],
    )


def scene_station_gate() -> dict[str, Any]:
    return make_scene(
        "ch02_station_gate",
        "第二章：废弃地铁站",
        "旧员工入口",
        "找到进入废弃站台的低风险路线。",
        "站外监控稀疏",
        "旧员工入口被铁链绕住，检修门旁贴着褪色编号。保安亭里还亮着一盏台灯，墙角摄像头盲区刚好覆盖半扇门。",
        [
            make_anchor(
                "obs_station_entry_code",
                "检修门",
                "查看检修门编号",
                1,
                [{"set": {"clues.station_entry_code": True}}],
                ["choice_enter_service_corridor"],
                "编号末尾是 0213。林把时间、订单和入口码叠在了一起。",
                ["pattern", "entry"],
            ),
            make_anchor(
                "obs_security_booth",
                "保安亭",
                "检查保安亭",
                1,
                [{"set": {"clues.security_booth": True}}],
                ["choice_wait_guard_shift"],
                "值班表被撕掉了一半。剩下的名字里有陈警官辖区的一名辅警。",
                ["chen", "risk"],
            ),
            make_anchor(
                "obs_camera_blind_spot",
                "摄像头盲区",
                "确认摄像头盲区",
                1,
                [{"set": {"clues.camera_blind_spot": True}}],
                ["choice_enter_service_corridor"],
                "盲区不是自然形成的，像是有人提前把摄像头角度偏了三度。",
                ["surveillance"],
                discoverability="subtle",
            ),
        ],
        [
            make_choice(
                "choice_enter_service_corridor",
                "从检修门进入",
                "你会避开正门摄像头，但进入后很难回头。",
                "ch02_station_platform",
                "检修门发出很轻的一声响，像是早就等着这个编号。",
                requirements=[{"state": "clues.station_entry_code", "equals": True}],
                effects=[{"add": {"stance.truth_first": 1}}],
            ),
            make_choice(
                "choice_wait_guard_shift",
                "等保安亭换班",
                "你会浪费时间，但可能减少被拍到的风险。",
                "ch02_station_platform",
                "十分钟后，台灯熄了。你错过一点窗口，也避开了一双眼睛。",
                requirements=[{"state": "clues.security_booth", "equals": True}],
                effects=[{"add": {"stance.protect_person": 1}}],
            ),
            make_choice(
                "choice_force_gate",
                "剪断铁链",
                "速度最快，也最容易留下痕迹。",
                "ch02_station_platform",
                "铁链落地的声音比你想象中响。远处有水滴声停了一下。",
                effects=[{"add": {"pressure.company_alert": 1}}],
            ),
            make_choice(
                "choice_call_chen_at_gate",
                "让陈确认入口安全",
                "如果他可信，这能少走弯路；如果不可信，你等于报点。",
                "ch02_station_platform",
                "陈说：“走检修门，别走正门。”他太快给出答案，让你更不安。",
                effects=[{"add": {"relationships.chen.trust": 1}}, {"add": {"relationships.chen.suspicion": 1}}],
            ),
        ],
        state_echoes=[
            make_echo(
                "echo_gate_chen_trust",
                "陈给过定位",
                "如果你选择过相信陈，他发来的定位点会和旧员工入口重合。这不是洗白，只是说明他至少没把你引向正门。",
                [{"state": "relationships.chen.trust", "min": 1}],
            ),
            make_echo(
                "echo_gate_chen_suspicion",
                "被陈看见的路线",
                "质问陈之后再来到这里，入口反而显得过于安静。你很难判断这是他的帮助，还是他的布置。",
                [{"state": "relationships.chen.suspicion", "min": 2}],
            ),
            make_echo(
                "echo_gate_lin_bond",
                "林的声音同行",
                "你备份过语音便签后，林的那句“别只救我”会在入口前再次响起，让这里不再只是一个坐标。",
                [{"state": "relationships.lin.bond", "min": 2}],
            ),
        ],
    )


def scene_station_platform() -> dict[str, Any]:
    return make_scene(
        "ch02_station_platform",
        "第二章：废弃地铁站",
        "废弃站台",
        "确认林在站台留下了什么。",
        "公司警报升高",
        "站台没有灯，只有手机屏幕照亮墙上的旧广告。广告背面贴着一张车票，票根上写着“别公开录音”。轨道旁的储物柜还亮着微弱红点。",
        [
            make_anchor(
                "obs_ticket",
                "车票",
                "取下车票",
                1,
                [{"set": {"clues.ticket_warning": True}}],
                [],
                "车票背面写着：录音是真的，剪辑是假的。底部还有一串储物柜编号：A-17。",
                ["recording", "locker"],
                [
                    make_anchor(
                        "obs_locker_code",
                        "A-17",
                        "核对储物柜编号",
                        2,
                        [{"set": {"clues.locker_a17": True}}],
                        ["choice_open_locker"],
                        "A-17 的柜门没有锁死，只要用手机靠近就能触发离线备份。",
                        ["backup"],
                        discoverability="subtle",
                    )
                ],
            ),
            make_anchor(
                "obs_red_dot",
                "微弱红点",
                "检查红点",
                1,
                [{"set": {"clues.hidden_camera": True}}],
                ["choice_cover_camera"],
                "红点来自一个临时摄像头。它正在上传低清画面，上传目的地仍是那套公司后台。",
                ["camera", "company"],
                discoverability="subtle",
            ),
            make_anchor(
                "obs_recording_warning",
                "别公开录音",
                "辨认字迹",
                1,
                [{"set": {"clues.lin_confession": True}}],
                ["choice_read_wall_note"],
                "这是林的字。她不是说录音不存在，而是在求你不要公开它。",
                ["lin", "moral_pressure"],
            ),
        ],
        [
            make_choice(
                "choice_wait_station",
                "继续等待",
                "你会错过清除前的窗口，但可能看清是谁在监视这里。",
                "ch02_locker_room",
                "五分钟后，摄像头自动转向了你。你等到了答案，也暴露了自己。",
                effects=[{"add": {"pressure.company_alert": 1}}],
            ),
            make_choice(
                "choice_open_locker",
                "打开 A-17 储物柜",
                "你会进入储物柜后方的维护间，那里可能有林留下的备份。",
                "ch02_locker_room",
                "柜门弹开，后面不是储物格，而是一条窄窄的维护通道。",
                requirements=[{"state": "clues.locker_a17", "equals": True}],
                effects=[{"set": {"clues.backup_copy": True}}, {"add": {"relationships.lin.bond": 1}}],
                consequence_level="global",
            ),
            make_choice(
                "choice_cover_camera",
                "遮住隐藏摄像头",
                "你能争取一点安全时间，但公司会知道有人发现了监控。",
                "ch02_locker_room",
                "画面中断。几乎同时，手机收到一条没有号码的短信：别再碰柜子。",
                requirements=[{"state": "clues.hidden_camera", "equals": True}],
                effects=[{"add": {"pressure.company_alert": 1}}],
            ),
            make_choice(
                "choice_read_wall_note",
                "带走写有警告的车票",
                "你会把林的请求放进行动记录里，而不只是把它当线索。",
                "ch02_locker_room",
                "车票被你折进手机壳。那句话变成了你后面每个选择的重量。",
                requirements=[{"state": "clues.lin_confession", "equals": True}],
                effects=[{"add": {"stance.protect_person": 1}}],
                consequence_level="global",
            ),
        ],
        state_echoes=[
            make_echo(
                "echo_platform_chen_trust",
                "陈的入口建议",
                "你若让陈确认过入口，站台上的摄像头角度会显得更像一次刻意放行，而不是偶然故障。",
                [{"state": "relationships.chen.trust", "min": 1}],
            ),
            make_echo(
                "echo_platform_chen_suspicion",
                "陈知道你在这里",
                "你越怀疑陈，站台就越像一间已经被人预留好的审讯室。没有脚步声，反而更像有人在等。",
                [{"state": "relationships.chen.suspicion", "min": 2}],
            ),
            make_echo(
                "echo_platform_lin_bond",
                "林不再只是失踪者",
                "语音便签被你保存后，票根上的字迹不再像证据，而像一个人把最难说出口的话递给你。",
                [{"state": "relationships.lin.bond", "min": 2}],
            ),
        ],
    )


def scene_locker_room() -> dict[str, Any]:
    return make_scene(
        "ch02_locker_room",
        "第二章：废弃地铁站",
        "储物柜后的维护间",
        "取走备份，并判断林想保护谁。",
        "脚步声接近",
        "维护间里有一块离线备份盘，一枚录音钥匙，以及挂在管道上的红色手环。手机自动弹出林留下的短句：别只救我。",
        [
            make_anchor(
                "obs_backup_drive",
                "离线备份",
                "读取离线备份",
                1,
                [{"set": {"clues.backup_copy": True}}],
                ["choice_take_backup_to_safehouse"],
                "备份盘里不是单个文件，而是一组互相校验的音频、短信和后台日志。",
                ["backup"],
            ),
            make_anchor(
                "obs_audio_key",
                "录音钥匙",
                "检查录音钥匙",
                1,
                [{"set": {"clues.lin_audio_key": True}}],
                ["choice_take_backup_to_safehouse"],
                "钥匙只解一半录音。另一半需要林手机里的本地日志配对。",
                ["recording", "key"],
            ),
            make_anchor(
                "obs_red_bracelet",
                "红色手环",
                "查看红色手环",
                1,
                [{"set": {"clues.victim_list": True}}, {"add": {"relationships.lin.bond": 1}}],
                ["choice_protect_lin_secret"],
                "手环内侧刻着三个名字。林不是唯一被卷进来的人。",
                ["victims", "lin"],
                discoverability="subtle",
            ),
        ],
        [
            make_choice(
                "choice_take_backup_to_safehouse",
                "带走备份盘和录音钥匙",
                "你会拿到完整证据链，也会成为公司最明确的目标。",
                "ch03_backup_unlock",
                "备份盘发热，手机开始配对。第二章到此收束成一个问题：真相到底伤害谁？",
                requirements=[{"state": "clues.backup_copy", "equals": True}],
                effects=[{"add": {"stance.truth_first": 1}}],
                consequence_level="global",
            ),
            make_choice(
                "choice_protect_lin_secret",
                "先遮住红色手环的信息",
                "你会保护其他受害者身份，但证据链会暂时不完整。",
                "ch03_backup_unlock",
                "你拍下手环，却把名字打码。林的秘密没有再扩大。",
                requirements=[{"state": "clues.victim_list", "equals": True}],
                effects=[{"add": {"stance.protect_person": 1}}],
                consequence_level="global",
            ),
            make_choice(
                "choice_destroy_locker_camera",
                "砸掉维护间摄像头",
                "你能阻止继续上传，但会留下非常明确的破坏痕迹。",
                "ch03_backup_unlock",
                "摄像头碎掉。手机震了一下，像是后台终于确认你在现场。",
                effects=[{"add": {"pressure.company_alert": 1}}],
            ),
            make_choice(
                "choice_wait_for_lin_contact",
                "等林预设的下一条消息",
                "你会多等两分钟，看她是否还留了别的条件。",
                "ch03_backup_unlock",
                "两分钟后只出现一句话：如果你已经到这里，别再相信单一证据。",
                effects=[{"add": {"relationships.lin.bond": 1}}],
            ),
        ],
        state_echoes=[
            make_echo(
                "echo_locker_lin_bond",
                "林的请求变重",
                "你越早把林当成一个具体的人，维护间里的“别只救我”就越不像提示，越像她在拒绝被单独拯救。",
                [{"state": "relationships.lin.bond", "min": 2}],
            ),
            make_echo(
                "echo_locker_chen_trust",
                "陈留下的缝隙",
                "如果陈曾帮你避开正门，这条维护通道就像他没有明说的第二句话：我不能救她，但可以让你进去。",
                [{"state": "relationships.chen.trust", "min": 2}],
            ),
        ],
    )


def scene_backup_unlock() -> dict[str, Any]:
    return make_scene(
        "ch03_backup_unlock",
        "第三章：被保存的副本",
        "解密备份",
        "还原录音与剪辑之间的差异。",
        "最后选择逼近",
        "备份解密完成。屏幕上有两份文件：原始录音和剪辑版本。校验区提示：仍缺少上下文证人链。",
        [
            make_anchor(
                "obs_raw_recording",
                "原始录音",
                "播放原始录音",
                1,
                [{"set": {"clues.raw_recording": True}}],
                ["choice_compare_context"],
                "原始录音能证明公司伪造证据，但也会暴露林曾经剪辑过另一段证词。",
                ["truth", "cost"],
            ),
            make_anchor(
                "obs_edited_recording",
                "剪辑版本",
                "比对剪辑版本",
                1,
                [{"set": {"clues.edited_recording": True}}],
                ["choice_send_hash_to_chen"],
                "剪辑版本删去了陈警官阻止上报的两句话，也删去了林承认自己曾经越界的一句。",
                ["chen", "lin"],
                discoverability="subtle",
            ),
            make_anchor(
                "obs_context_chain",
                "上下文证人链",
                "查看证人链缺口",
                1,
                [{"set": {"clues.victim_list": True}}],
                ["choice_archive_first"],
                "证人链里有三个匿名名字，对应你在维护间看到的红色手环。",
                ["victims"],
            ),
        ],
        [
            make_choice(
                "choice_compare_context",
                "继续查证人链",
                "你会延后发布，先弄清录音会伤到哪些人。",
                "ch03_witness_thread",
                "原始录音被暂存。你打开证人链，林留下的最后留言开始浮现。",
                requirements=[{"state": "clues.raw_recording", "equals": True}],
                effects=[{"add": {"stance.truth_first": 1}}],
                consequence_level="global",
            ),
            make_choice(
                "choice_send_hash_to_chen",
                "把剪辑哈希发给陈",
                "你给他最后一次解释机会，也让他知道你快要公开。",
                "ch03_witness_thread",
                "陈回了一个句号。几秒后，他又发来：先看最后留言。",
                requirements=[{"state": "clues.edited_recording", "equals": True}],
                effects=[{"add": {"relationships.chen.suspicion": 1}}],
            ),
            make_choice(
                "choice_archive_first",
                "先做离线封存",
                "你会保证证据不消失，但发布窗口会变窄。",
                "ch03_witness_thread",
                "证据被封存两份，一份在你手里，一份在手机自己生成的死信箱里。",
                requirements=[{"state": "clues.victim_list", "equals": True}],
                effects=[{"add": {"stance.protect_person": 1}}],
            ),
            make_choice(
                "choice_skip_context",
                "跳过上下文直接进入发布页",
                "你会更快触达结局，也更容易误伤。",
                "ch03_publish_decision",
                "发布页提前打开。缺失的证人链像空白栏一样刺眼。",
                effects=[{"add": {"pressure.company_alert": 1}}],
                consequence_level="global",
            ),
        ],
        state_echoes=[
            make_echo(
                "echo_backup_lin_bond",
                "备份不是遗物",
                "如果你已经和林建立了更强关联，备份解密时就不再像打开遗物，而像接过一个仍在发烫的决定。",
                [{"state": "relationships.lin.bond", "min": 2}],
            ),
            make_echo(
                "echo_backup_chen_suspicion",
                "陈的沉默压在录音上",
                "你越早逼近陈，剪辑版本就越像一场还没结束的对话。他的沉默不是空白，而是一种选择。",
                [{"state": "relationships.chen.suspicion", "min": 2}],
            ),
        ],
    )


def scene_witness_thread() -> dict[str, Any]:
    return make_scene(
        "ch03_witness_thread",
        "第三章：被保存的副本",
        "最后留言串",
        "判断真相公开前必须保留哪些上下文。",
        "证人链不完整",
        "留言串按时间展开。最后留言写着：“真相不是没有代价。” 受害者名单被打码，陈的停顿夹在两段录音之间。",
        [
            make_anchor(
                "obs_final_message",
                "最后留言",
                "阅读最后留言",
                1,
                [{"set": {"clues.final_message": True}}],
                ["choice_prepare_archive"],
                "她没有请求你救她。她只请求你在公开之前，先想清楚谁会因此被毁掉。",
                ["moral_pressure"],
            ),
            make_anchor(
                "obs_victim_list",
                "受害者名单",
                "核对受害者名单",
                1,
                [{"set": {"clues.victim_list": True}}],
                ["choice_prepare_public_packet"],
                "名单里有人仍在公司任职。如果公开没有遮罩，他们会先被找到。",
                ["victims", "risk"],
            ),
            make_anchor(
                "obs_chen_pause",
                "陈的停顿",
                "重听陈的停顿",
                1,
                [{"set": {"clues.chen_motive": True}}],
                ["choice_ask_chen_last_time"],
                "陈停顿的地方不是删词，而是在等林把一句话说完：别让他们只抓我。",
                ["chen", "motive"],
                discoverability="subtle",
            ),
        ],
        [
            make_choice(
                "choice_prepare_public_packet",
                "整理带遮罩的公开包",
                "你会公开核心证据，同时尽量保护名单里的人。",
                "ch03_publish_decision",
                "公开包生成了两版：一版完整，一版遮住了仍有风险的人名。",
                requirements=[{"state": "clues.victim_list", "equals": True}],
                effects=[{"set": {"clues.public_packet_ready": True}}, {"add": {"stance.truth_first": 1}}],
                consequence_level="global",
            ),
            make_choice(
                "choice_prepare_archive",
                "整理只给律师的封存包",
                "你会降低公开冲击，但可能让公司有时间反制。",
                "ch03_publish_decision",
                "封存包被打上时间戳。它更稳，也更慢。",
                requirements=[{"state": "clues.final_message", "equals": True}],
                effects=[{"set": {"clues.archive_ready": True}}, {"add": {"stance.protect_person": 1}}],
                consequence_level="global",
            ),
            make_choice(
                "choice_ask_chen_last_time",
                "最后一次询问陈",
                "你会把陈重新拉进局面，逼他承担自己的停顿。",
                "ch03_publish_decision",
                "陈发来一段未剪辑录音。他没有洗清自己，但补上了一块缺口。",
                requirements=[{"state": "clues.chen_motive", "equals": True}],
                effects=[{"set": {"clues.chen_message_ready": True}}, {"add": {"relationships.chen.trust": 1}}],
            ),
            make_choice(
                "choice_enter_decision_without_more",
                "带着缺口进入发布页",
                "你接受不完整性，让选择本身承担后果。",
                "ch03_publish_decision",
                "发布页打开，三个空白栏还在提醒你：你并没有掌握全部。",
                effects=[{"add": {"pressure.company_alert": 1}}],
            ),
        ],
        state_echoes=[
            make_echo(
                "echo_witness_lin_bond",
                "林要求你看见别人",
                "你和林的关联越深，受害者名单就越刺眼：她不是要你替她赢，而是要你别让其他人继续输。",
                [{"state": "relationships.lin.bond", "min": 2}],
            ),
            make_echo(
                "echo_witness_chen_trust",
                "陈补上的缺口",
                "如果陈已经给过你帮助，他在录音里的停顿会显得更具体：那不是勇敢，也不是背叛，是他一直没有付清的代价。",
                [{"state": "relationships.chen.trust", "min": 2}],
            ),
            make_echo(
                "echo_witness_chen_suspicion",
                "陈仍在场",
                "你越怀疑陈，他的停顿越像一次控制现场的手段。现在你必须决定还要不要把解释权交给他。",
                [{"state": "relationships.chen.suspicion", "min": 2}],
            ),
        ],
    )


def scene_publish_decision() -> dict[str, Any]:
    return make_scene(
        "ch03_publish_decision",
        "第三章：被保存的副本",
        "发布页",
        "决定真相以什么形式进入世界。",
        "最后选择",
        "发布页等待确认。公开包、离线存储和发给陈的草稿并排亮着。每一项都能保存一部分真相，也会牺牲另一部分人。",
        [
            make_anchor(
                "obs_public_packet",
                "公开包",
                "检查公开包",
                1,
                [{"set": {"clues.public_packet_ready": True}}],
                ["choice_publish_truth"],
                "公开包能把公司拖到灯下。即使遮住名单，林曾经越界的事实仍会被看见。",
                ["truth", "public"],
            ),
            make_anchor(
                "obs_offline_archive",
                "离线存储",
                "检查离线存储",
                1,
                [{"set": {"clues.archive_ready": True}}],
                ["choice_keep_archive"],
                "离线存储会保住证据，但它不会自动替任何人说话。",
                ["archive", "delay"],
            ),
            make_anchor(
                "obs_send_to_chen",
                "发给陈",
                "检查发给陈的草稿",
                1,
                [{"set": {"clues.chen_message_ready": True}}],
                ["choice_confront_final"],
                "草稿里只有一句话：这次你不能再停顿。",
                ["chen", "confront"],
                discoverability="subtle",
            ),
        ],
        [
            make_choice(
                "choice_publish_truth",
                "公开原始录音",
                "公司会被迫回应，林的污点也会一起暴露。",
                "ending_publish",
                "你按下发布。上传条走到尽头时，手机终于被远程清除。",
                requirements=[{"state": "clues.public_packet_ready", "equals": True}],
                effects=[{"add": {"stance.truth_first": 2}}],
                consequence_level="ending",
            ),
            make_choice(
                "choice_keep_archive",
                "保存但暂不公开",
                "你保住证据，也选择暂时替所有人守住秘密。",
                "ending_bury",
                "你把副本转入离线存储。屏幕黑掉之前，最后一条日志显示：清除完成。",
                requirements=[{"state": "clues.archive_ready", "equals": True}],
                effects=[{"add": {"stance.protect_person": 2}}],
                consequence_level="ending",
            ),
            make_choice(
                "choice_confront_final",
                "把剪辑痕迹发给陈",
                "你逼他解释那两句话，但公司可能正在监听。",
                "ending_confront",
                "陈只回了四个字：现在别发。下一秒，远程会话接管了屏幕。",
                requirements=[{"state": "clues.chen_message_ready", "equals": True}],
                effects=[{"add": {"relationships.chen.suspicion": 1}}, {"add": {"pressure.company_alert": 1}}],
                consequence_level="ending",
            ),
        ],
        state_echoes=[
            make_echo(
                "echo_publish_lin_bond",
                "林仍在选择里",
                "你和林的关联越深，发布页越不像一个按钮，而像一次你替她承担但不能替她消失的判断。",
                [{"state": "relationships.lin.bond", "min": 2}],
            ),
            make_echo(
                "echo_publish_chen_trust",
                "陈的补证",
                "如果陈最后补上了录音缺口，发给陈的草稿会少一点报复感，多一点逼他公开站出来的重量。",
                [{"state": "relationships.chen.trust", "min": 2}],
            ),
            make_echo(
                "echo_publish_chen_suspicion",
                "陈仍可能切断你",
                "你越怀疑陈，发布页里的每一次停顿都像倒计时。把草稿发给他，可能是在给他最后一次切断你的机会。",
                [{"state": "relationships.chen.suspicion", "min": 2}],
            ),
        ],
    )


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
        for echo in scene.get("state_echoes", []):
            for requirement in echo.get("requirements", []):
                if requirement.get("state"):
                    ensure(requirement["state"])["reads"].append(f"{scene_id}.{echo['id']}.requirements")
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
