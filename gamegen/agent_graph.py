from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from scripts.content_qa_report import ContentQAMessage, run_content_qa
from scripts.repair_game import repair_game

from .blueprint_alignment import BlueprintAlignmentMessage, validate_blueprint_alignment
from .demo_agent import (
    OFFLINE_MODEL_ID,
    apply_llm_polish,
    export_game,
    load_brief,
)
from .llm_client import LLMClient, LLMConfig
from .schema_contract import validate_against_default_schema
from .scene_artifacts import (
    SceneArtifactMessage,
    build_scene_artifacts_from_library,
    compile_game_from_scene_artifacts,
    review_scene_artifacts,
    validate_scene_artifact_release,
    validate_scene_artifacts,
)
from .scene_blueprint import (
    SceneBlueprintMessage,
    build_scene_blueprint_design,
    validate_scene_blueprint_design,
)
from .state_schema_design import StateSchemaDesignMessage, validate_state_schema_design
from .validator import ValidationMessage, validate_game


Provider = Literal["auto", "offline", "llm"]


class AgentRunError(RuntimeError):
    pass


@dataclass
class TraceEvent:
    node: str
    status: str
    summary: str
    metrics: dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> str:
        return json.dumps(
            {
                "node": self.node,
                "status": self.status,
                "summary": self.summary,
                "metrics": self.metrics,
            },
            ensure_ascii=False,
        )


@dataclass
class AgentConfig:
    brief_path: Path
    out_dir: Path
    provider: Provider = "auto"
    max_repair_attempts: int = 1


@dataclass
class AgentState:
    config: AgentConfig
    brief: dict[str, Any] | None = None
    generation_plan: dict[str, Any] | None = None
    state_schema_design: dict[str, Any] | None = None
    scene_blueprint_design: dict[str, Any] | None = None
    scene_artifacts: dict[str, Any] | None = None
    game: dict[str, Any] | None = None
    state_schema_messages: list[StateSchemaDesignMessage] = field(default_factory=list)
    scene_blueprint_messages: list[SceneBlueprintMessage] = field(default_factory=list)
    scene_artifact_messages: list[SceneArtifactMessage] = field(default_factory=list)
    scene_artifact_release_messages: list[SceneArtifactMessage] = field(default_factory=list)
    blueprint_alignment_messages: list[BlueprintAlignmentMessage] = field(default_factory=list)
    schema_errors: list[str] = field(default_factory=list)
    validation_messages: list[ValidationMessage] = field(default_factory=list)
    content_qa_messages: list[ContentQAMessage] = field(default_factory=list)
    repairs: list[str] = field(default_factory=list)
    repair_attempts: int = 0
    exported: bool = False
    trace_events: list[TraceEvent] = field(default_factory=list)

    def add_trace(self, node: str, status: str, summary: str, **metrics: Any) -> None:
        self.trace_events.append(TraceEvent(node=node, status=status, summary=summary, metrics=metrics))

    def blocking_error_count(self) -> int:
        state_schema_errors = sum(1 for message in self.state_schema_messages if message.level == "error")
        scene_blueprint_errors = sum(1 for message in self.scene_blueprint_messages if message.level == "error")
        scene_artifact_errors = sum(1 for message in self.scene_artifact_messages if message.level == "error")
        scene_artifact_release_errors = sum(
            1 for message in self.scene_artifact_release_messages if message.level == "error"
        )
        blueprint_alignment_errors = sum(1 for message in self.blueprint_alignment_messages if message.level == "error")
        validation_errors = sum(1 for message in self.validation_messages if message.level == "error")
        content_errors = sum(1 for message in self.content_qa_messages if message.level == "error")
        return (
            state_schema_errors
            + scene_blueprint_errors
            + scene_artifact_errors
            + scene_artifact_release_errors
            + blueprint_alignment_errors
            + len(self.schema_errors)
            + validation_errors
            + content_errors
        )


class GenerationAgentGraph:
    def run(self, config: AgentConfig) -> AgentState:
        state = AgentState(config=config)
        self.load_brief(state)
        self.plan_story_structure(state)
        self.design_state_schema(state)
        self.validate_state_schema_design(state)
        self.design_scene_blueprint(state)
        self.validate_scene_blueprint(state)
        self.draft_scene_artifacts(state)
        self.validate_scene_artifacts(state)
        self.review_scene_artifacts(state)
        self.validate_scene_artifact_release(state)
        self.draft_skeleton(state)
        self.validate_blueprint_alignment(state)
        self.optional_llm_polish(state)

        while True:
            self.validate_schema(state)
            self.validate_structure(state)
            self.validate_content_qa(state)
            if state.blocking_error_count() == 0:
                state.add_trace(
                    "repair_if_needed",
                    "skipped",
                    "All validation gates passed; no repair needed",
                    repair_attempts=state.repair_attempts,
                )
                break
            self.repair_if_needed(state)

        self.export_artifacts(state)
        self.write_agent_trace(state)
        return state

    def load_brief(self, state: AgentState) -> None:
        state.brief = load_brief(state.config.brief_path)
        state.add_trace(
            "load_brief",
            "ok",
            "Loaded project brief",
            brief_path=str(state.config.brief_path),
            project_id=state.brief.get("project", {}).get("id"),
        )

    def draft_skeleton(self, state: AgentState) -> None:
        if (
            state.brief is None
            or state.generation_plan is None
            or state.state_schema_design is None
            or state.scene_blueprint_design is None
            or state.scene_artifacts is None
        ):
            raise AgentRunError("draft_skeleton requires loaded brief, generation plan, state schema design, scene blueprint, and scene artifacts")
        state.game = compile_game_from_scene_artifacts(state.brief, state.scene_artifacts)
        generation = state.game.setdefault("generation", {})
        generation["provider"] = "offline"
        generation["model"] = OFFLINE_MODEL_ID
        generation["agent_graph"] = "v0_36"
        generation["plan_schema_version"] = state.generation_plan["plan_schema_version"]
        generation["state_schema_design_version"] = state.state_schema_design["schema_version"]
        generation["scene_blueprint_version"] = state.scene_blueprint_design["schema_version"]
        generation["scene_artifacts_version"] = state.scene_artifacts["schema_version"]
        state.add_trace(
            "draft_skeleton",
            "ok",
            "Created deterministic structured game skeleton",
            planned_chapters=state.generation_plan["chapter_count"],
            planned_scenes=state.generation_plan["scene_count"],
            designed_state_variables=len(state.state_schema_design["variables"]),
            planned_blueprint_scenes=len(state.scene_blueprint_design["scenes"]),
            draft_source=generation["draft_source"],
            scene_artifacts=len(state.scene_artifacts["artifacts"]),
            locked_scene_artifacts=sum(1 for artifact in state.scene_artifacts["artifacts"] if artifact["status"] == "locked"),
            scenes=len(state.game.get("scenes", [])),
            endings=len(state.game.get("endings", [])),
        )

    def plan_story_structure(self, state: AgentState) -> None:
        if state.brief is None:
            raise AgentRunError("plan_story_structure requires loaded brief")
        state.generation_plan = build_generation_plan(state.brief)
        state.add_trace(
            "plan_story_structure",
            "ok",
            "Built deterministic generation plan",
            chapters=state.generation_plan["chapter_count"],
            scenes=state.generation_plan["scene_count"],
            ending_targets=len(state.generation_plan["ending_targets"]),
        )

    def design_state_schema(self, state: AgentState) -> None:
        if state.brief is None or state.generation_plan is None:
            raise AgentRunError("design_state_schema requires loaded brief and generation plan")
        state.state_schema_design = build_state_schema_design(state.brief, state.generation_plan)
        state.add_trace(
            "design_state_schema",
            "ok",
            "Designed hidden state schema",
            axes=len(state.state_schema_design["axes"]),
            variables=len(state.state_schema_design["variables"]),
            relationship_axes=len(state.state_schema_design["relationship_axes"]),
        )

    def validate_state_schema_design(self, state: AgentState) -> None:
        if state.state_schema_design is None:
            raise AgentRunError("validate_state_schema_design requires state schema design")
        state.state_schema_messages = validate_state_schema_design(state.state_schema_design)
        errors = sum(1 for message in state.state_schema_messages if message.level == "error")
        warnings = sum(1 for message in state.state_schema_messages if message.level == "warning")
        state.add_trace(
            "validate_state_schema_design",
            "ok" if errors == 0 else "error",
            "State schema design gate completed",
            errors=errors,
            warnings=warnings,
        )
        if errors:
            raise AgentRunError("State schema design failed validation")

    def design_scene_blueprint(self, state: AgentState) -> None:
        if state.brief is None or state.generation_plan is None or state.state_schema_design is None:
            raise AgentRunError("design_scene_blueprint requires brief, generation plan, and state schema design")
        state.scene_blueprint_design = build_scene_blueprint_design(
            state.brief,
            state.generation_plan,
            state.state_schema_design,
        )
        ending_scene_count = sum(1 for scene in state.scene_blueprint_design["scenes"] if scene["ending_targets"])
        state.add_trace(
            "design_scene_blueprint",
            "ok",
            "Designed scene blueprint contract",
            scenes=len(state.scene_blueprint_design["scenes"]),
            ending_scene_count=ending_scene_count,
        )

    def validate_scene_blueprint(self, state: AgentState) -> None:
        if state.scene_blueprint_design is None or state.generation_plan is None or state.state_schema_design is None:
            raise AgentRunError("validate_scene_blueprint requires scene blueprint, generation plan, and state schema design")
        state.scene_blueprint_messages = validate_scene_blueprint_design(
            state.scene_blueprint_design,
            state.generation_plan,
            state.state_schema_design,
        )
        errors = sum(1 for message in state.scene_blueprint_messages if message.level == "error")
        warnings = sum(1 for message in state.scene_blueprint_messages if message.level == "warning")
        state.add_trace(
            "validate_scene_blueprint",
            "ok" if errors == 0 else "error",
            "Scene blueprint gate completed",
            errors=errors,
            warnings=warnings,
        )
        if errors:
            raise AgentRunError("Scene blueprint failed validation")

    def draft_scene_artifacts(self, state: AgentState) -> None:
        if state.brief is None or state.scene_blueprint_design is None:
            raise AgentRunError("draft_scene_artifacts requires brief and scene blueprint")
        try:
            state.scene_artifacts = build_scene_artifacts_from_library(state.brief, state.scene_blueprint_design)
        except ValueError as exc:
            state.add_trace("draft_scene_artifacts", "error", "Scene artifacts could not be drafted", error=str(exc))
            raise AgentRunError(str(exc)) from exc
        state.add_trace(
            "draft_scene_artifacts",
            "ok",
            "Drafted scene artifacts from demo scene library",
            artifacts=len(state.scene_artifacts["artifacts"]),
            source="demo_scene_library_v0_1",
        )

    def validate_scene_artifacts(self, state: AgentState) -> None:
        if state.scene_artifacts is None or state.scene_blueprint_design is None:
            raise AgentRunError("validate_scene_artifacts requires scene artifacts and scene blueprint")
        state.scene_artifact_messages = validate_scene_artifacts(state.scene_artifacts, state.scene_blueprint_design)
        errors = sum(1 for message in state.scene_artifact_messages if message.level == "error")
        warnings = sum(1 for message in state.scene_artifact_messages if message.level == "warning")
        state.add_trace(
            "validate_scene_artifacts",
            "ok" if errors == 0 else "error",
            "Scene artifact gate completed",
            errors=errors,
            warnings=warnings,
        )
        if errors:
            raise AgentRunError("Scene artifacts failed validation")

    def review_scene_artifacts(self, state: AgentState) -> None:
        if state.scene_artifacts is None:
            raise AgentRunError("review_scene_artifacts requires scene artifacts")
        state.scene_artifacts = review_scene_artifacts(state.scene_artifacts)
        locked_count = sum(1 for artifact in state.scene_artifacts["artifacts"] if artifact["status"] == "locked")
        state.add_trace(
            "review_scene_artifacts",
            "ok",
            "Reviewed and locked scene artifacts for compile",
            locked=locked_count,
            reviewer="deterministic_reviewer_v0_1",
        )

    def validate_scene_artifact_release(self, state: AgentState) -> None:
        if state.scene_artifacts is None:
            raise AgentRunError("validate_scene_artifact_release requires scene artifacts")
        state.scene_artifact_release_messages = validate_scene_artifact_release(state.scene_artifacts)
        errors = sum(1 for message in state.scene_artifact_release_messages if message.level == "error")
        warnings = sum(1 for message in state.scene_artifact_release_messages if message.level == "warning")
        state.add_trace(
            "validate_scene_artifact_release",
            "ok" if errors == 0 else "error",
            "Scene artifact release gate completed",
            errors=errors,
            warnings=warnings,
        )
        if errors:
            raise AgentRunError("Scene artifact release failed validation")

    def validate_blueprint_alignment(self, state: AgentState) -> None:
        if state.game is None or state.scene_blueprint_design is None:
            raise AgentRunError("validate_blueprint_alignment requires game and scene blueprint")
        state.blueprint_alignment_messages = validate_blueprint_alignment(state.game, state.scene_blueprint_design)
        errors = sum(1 for message in state.blueprint_alignment_messages if message.level == "error")
        warnings = sum(1 for message in state.blueprint_alignment_messages if message.level == "warning")
        state.add_trace(
            "validate_blueprint_alignment",
            "ok" if errors == 0 else "error",
            "Blueprint-to-game alignment gate completed",
            errors=errors,
            warnings=warnings,
        )
        if errors:
            raise AgentRunError("Blueprint-to-game alignment failed validation")

    def optional_llm_polish(self, state: AgentState) -> None:
        if state.game is None or state.brief is None:
            raise AgentRunError("optional_llm_polish requires game and brief")
        provider = state.config.provider
        if provider == "offline":
            state.add_trace("optional_llm_polish", "skipped", "Provider is offline")
            return

        config = LLMConfig.from_env()
        if not config:
            if provider == "llm":
                state.add_trace("optional_llm_polish", "error", "LLM provider requested but env is missing")
                raise AgentRunError("LLM provider requested, but LLM_BASE_URL or LLM_API_KEY is missing")
            state.add_trace("optional_llm_polish", "skipped", "No OpenAI-compatible env configured")
            return

        try:
            apply_llm_polish(state.game, state.brief, LLMClient(config))
        except Exception as exc:  # noqa: BLE001 - graph records fallback instead of crashing auto mode
            generation = state.game.setdefault("generation", {})
            generation["provider"] = "offline_fallback"
            generation["model"] = config.model
            generation["llm_error"] = str(exc)
            state.add_trace("optional_llm_polish", "fallback", "LLM polish failed; kept deterministic text")
            if provider == "llm":
                raise AgentRunError(f"LLM polish failed: {exc}") from exc
            return

        generation = state.game.setdefault("generation", {})
        generation["provider"] = "openai_compatible"
        generation["model"] = config.model
        state.add_trace("optional_llm_polish", "ok", "Applied constrained LLM polish", model=config.model)

    def validate_schema(self, state: AgentState) -> None:
        if state.game is None:
            raise AgentRunError("validate_schema requires game")
        state.schema_errors = validate_against_default_schema(state.game)
        status = "ok" if not state.schema_errors else "error"
        state.add_trace(
            "validate_schema",
            status,
            "JSON Schema gate completed",
            errors=len(state.schema_errors),
        )

    def validate_structure(self, state: AgentState) -> None:
        if state.game is None:
            raise AgentRunError("validate_structure requires game")
        state.validation_messages = validate_game(state.game)
        errors = sum(1 for message in state.validation_messages if message.level == "error")
        warnings = sum(1 for message in state.validation_messages if message.level == "warning")
        state.add_trace(
            "validate_structure",
            "ok" if errors == 0 else "error",
            "Graph and state validator gate completed",
            errors=errors,
            warnings=warnings,
        )

    def validate_content_qa(self, state: AgentState) -> None:
        if state.game is None:
            raise AgentRunError("validate_content_qa requires game")
        state.content_qa_messages = run_content_qa(state.game)
        errors = sum(1 for message in state.content_qa_messages if message.level == "error")
        warnings = sum(1 for message in state.content_qa_messages if message.level == "warning")
        state.add_trace(
            "validate_content_qa",
            "ok" if errors == 0 else "error",
            "Content QA gate completed",
            errors=errors,
            warnings=warnings,
        )

    def repair_if_needed(self, state: AgentState) -> None:
        if state.game is None:
            raise AgentRunError("repair_if_needed requires game")
        if state.repair_attempts >= state.config.max_repair_attempts:
            state.add_trace(
                "repair_if_needed",
                "error",
                "Repair limit reached",
                repair_attempts=state.repair_attempts,
                blocking_errors=state.blocking_error_count(),
            )
            raise AgentRunError("Agent graph failed validation and repair limit was reached")

        state.repair_attempts += 1
        repaired, repairs = repair_game(state.game)
        state.repairs.extend(repairs)
        if not repairs:
            state.add_trace(
                "repair_if_needed",
                "error",
                "No supported repairs available for current blocking errors",
                repair_attempts=state.repair_attempts,
                blocking_errors=state.blocking_error_count(),
            )
            raise AgentRunError("Agent graph failed validation and no supported repairs were available")

        state.game = repaired
        state.add_trace(
            "repair_if_needed",
            "ok",
            "Applied conservative structural repairs",
            repair_attempts=state.repair_attempts,
            repairs=len(repairs),
        )

    def export_artifacts(self, state: AgentState) -> None:
        if (
            state.game is None
            or state.generation_plan is None
            or state.state_schema_design is None
            or state.scene_blueprint_design is None
            or state.scene_artifacts is None
        ):
            raise AgentRunError("export_artifacts requires game, generation plan, state schema design, scene blueprint, and scene artifacts")
        export_game(state.game, state.config.out_dir)
        (state.config.out_dir / "generation_plan.json").write_text(
            json.dumps(state.generation_plan, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        (state.config.out_dir / "state_schema_design.json").write_text(
            json.dumps(state.state_schema_design, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        (state.config.out_dir / "scene_blueprint.json").write_text(
            json.dumps(state.scene_blueprint_design, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        (state.config.out_dir / "scene_artifacts.json").write_text(
            json.dumps(state.scene_artifacts, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        state.exported = True
        state.add_trace(
            "export_artifacts",
            "ok",
            "Exported game artifacts",
            out_dir=str(state.config.out_dir),
        )

    def write_agent_trace(self, state: AgentState) -> None:
        state.config.out_dir.mkdir(parents=True, exist_ok=True)
        trace_path = state.config.out_dir / "agent_trace.jsonl"
        trace_path.write_text(
            "\n".join(event.to_json() for event in state.trace_events) + "\n",
            encoding="utf-8",
        )
        state.add_trace("write_agent_trace", "ok", "Wrote agent trace", trace_path=str(trace_path))
        trace_path.write_text(
            "\n".join(event.to_json() for event in state.trace_events) + "\n",
            encoding="utf-8",
        )


def run_generation_agent(
    brief_path: str | Path,
    out_dir: str | Path,
    provider: Provider = "auto",
    max_repair_attempts: int = 1,
) -> AgentState:
    config = AgentConfig(
        brief_path=Path(brief_path),
        out_dir=Path(out_dir),
        provider=provider,
        max_repair_attempts=max_repair_attempts,
    )
    return GenerationAgentGraph().run(config)


def build_generation_plan(brief: dict[str, Any]) -> dict[str, Any]:
    project = brief["project"]
    world = brief["world"]
    return {
        "plan_schema_version": "generation_plan_v0_1",
        "project_id": project["id"],
        "title": project["title"],
        "theme_question": project["theme_question"],
        "target_duration_minutes": project.get("target_duration_minutes", 25),
        "interface": world["interface"],
        "chapter_count": 3,
        "scene_count": 9,
        "chapters": [
            {
                "id": "ch01",
                "title": "锁屏上的半句话",
                "chapter_question": "玩家是否会在证据不足时信任陈，还是先保护手机里的线索？",
                "scene_budget": 3,
            },
            {
                "id": "ch02",
                "title": "废弃地铁站",
                "chapter_question": "玩家会优先拿到真相，还是降低暴露他人的风险？",
                "scene_budget": 3,
            },
            {
                "id": "ch03",
                "title": "被保存的副本",
                "chapter_question": "玩家会如何让真相进入世界，并承担它伤害谁的后果？",
                "scene_budget": 3,
            },
        ],
        "state_axes": ["clues", "stance", "relationships", "pressure"],
        "ending_targets": ["ending_publish", "ending_bury", "ending_confront"],
        "non_goals": [
            "runtime_ai_story_generation",
            "free_text_player_input",
            "unbounded_branching",
        ],
    }


def build_state_schema_design(brief: dict[str, Any], generation_plan: dict[str, Any]) -> dict[str, Any]:
    project = brief["project"]
    variables = [
        state_variable("clues.unsent_warning", "clues", "boolean", False, "玩家是否理解短信在警告陈。", ["obs_unsent_sms"], ["chapter_review", "ending_profile"]),
        state_variable("clues.station_location", "clues", "boolean", False, "玩家是否取得废弃地铁站定位。", ["obs_0213_log"], ["choice_go_station", "chapter_review"]),
        state_variable("clues.chen_trimmed_location", "clues", "boolean", False, "玩家是否发现陈截断定位记录。", ["obs_trimmed_gap"], ["choice_confront_chen", "ending_confront"]),
        state_variable("clues.wipe_pause_window", "clues", "boolean", False, "玩家是否找到远程清除暂停窗口。", ["obs_pause_window"], ["choice_delay_wipe"]),
        state_variable("clues.freeze_token", "clues", "boolean", False, "玩家是否复制冻结令牌。", ["obs_session_token"], ["choice_freeze_wipe"]),
        state_variable("clues.station_entry_code", "clues", "boolean", False, "玩家是否获得旧员工入口码。", ["obs_station_entry_code"], ["choice_enter_service_corridor"]),
        state_variable("clues.locker_a17", "clues", "boolean", False, "玩家是否找到 A-17 储物柜编号。", ["obs_locker_code"], ["choice_open_locker"]),
        state_variable("clues.backup_copy", "clues", "boolean", False, "玩家是否取得离线备份。", ["obs_backup_drive", "choice_open_locker"], ["choice_take_backup_to_safehouse"]),
        state_variable("clues.victim_list", "clues", "boolean", False, "玩家是否知道受害者名单风险。", ["obs_red_bracelet", "obs_victim_list"], ["choice_prepare_public_packet", "choice_protect_lin_secret"]),
        state_variable("clues.public_packet_ready", "clues", "boolean", False, "玩家是否准备公开包。", ["choice_prepare_public_packet", "obs_public_packet"], ["choice_publish_truth"]),
        state_variable("clues.archive_ready", "clues", "boolean", False, "玩家是否准备封存包。", ["choice_prepare_archive", "obs_offline_archive"], ["choice_keep_archive"]),
        state_variable("clues.chen_message_ready", "clues", "boolean", False, "玩家是否准备发给陈的草稿。", ["choice_ask_chen_last_time", "obs_send_to_chen"], ["choice_confront_final"]),
        state_variable("stance.truth_first", "stance", "integer", 0, "玩家偏向公开真相的程度。", ["choice_go_station", "choice_enter_service_corridor"], ["ending_profile", "ending_publish"]),
        state_variable("stance.protect_person", "stance", "integer", 0, "玩家偏向保护具体人的程度。", ["choice_wait_guard_shift", "choice_prepare_archive"], ["ending_profile", "ending_bury"]),
        state_variable("relationships.chen.trust", "relationships", "integer", 0, "陈对玩家的信任/玩家选择相信陈的轨迹。", ["choice_call_chen", "choice_ask_chen_last_time"], ["state_echoes", "ending_profile"]),
        state_variable("relationships.chen.suspicion", "relationships", "integer", 0, "玩家对陈的怀疑和陈的警觉。", ["choice_confront_chen", "choice_confront_final"], ["state_echoes", "ending_confront"]),
        state_variable("relationships.lin.bond", "relationships", "integer", 0, "玩家与林留下请求之间的情感连接。", ["choice_open_locker", "obs_red_bracelet"], ["state_echoes", "ending_profile"]),
        state_variable("pressure.company_alert", "pressure", "integer", 0, "公司警报/暴露风险。", ["obs_remote_wipe", "choice_freeze_wipe", "choice_cover_camera"], ["state_echoes", "ending_profile"]),
    ]
    return {
        "schema_version": "state_schema_design_v0_1",
        "project_id": project["id"],
        "source_plan_schema_version": generation_plan["plan_schema_version"],
        "axes": [
            {"id": "clues", "purpose": "玩家已经确认的证据和可行动信息。"},
            {"id": "stance", "purpose": "玩家在道德问题上的倾向，而不是显式阵营。"},
            {"id": "relationships", "purpose": "隐藏关系向量，避免单一好感度条。"},
            {"id": "pressure", "purpose": "外部风险与时间压力。"},
        ],
        "variables": variables,
        "relationship_axes": {
            "chen": ["trust", "suspicion"],
            "lin": ["bond"],
        },
        "ending_tags": generation_plan["ending_targets"],
        "design_rules": [
            "隐藏关系变量必须通过文本回声表现，不能裸露数值。",
            "关键 choice 的 requirements 必须能被 observe 或前置 choice 明确写入。",
            "重大关系变化必须有文本暗示。",
            "pressure 只能改变风险语境，不能黑箱改写玩家意图。",
        ],
    }


def state_variable(
    key: str,
    axis: str,
    value_type: str,
    initial: bool | int,
    purpose: str,
    written_by: list[str],
    read_by: list[str],
) -> dict[str, Any]:
    return {
        "key": key,
        "axis": axis,
        "type": value_type,
        "initial": initial,
        "purpose": purpose,
        "written_by": written_by,
        "read_by": read_by,
    }
