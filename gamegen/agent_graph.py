from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from scripts.content_qa_report import ContentQAMessage, run_content_qa
from scripts.repair_game import repair_game

from .demo_agent import (
    OFFLINE_MODEL_ID,
    apply_llm_polish,
    deterministic_demo_game,
    export_game,
    load_brief,
)
from .llm_client import LLMClient, LLMConfig
from .schema_contract import validate_against_default_schema
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
    game: dict[str, Any] | None = None
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
        validation_errors = sum(1 for message in self.validation_messages if message.level == "error")
        content_errors = sum(1 for message in self.content_qa_messages if message.level == "error")
        return len(self.schema_errors) + validation_errors + content_errors


class GenerationAgentGraph:
    def run(self, config: AgentConfig) -> AgentState:
        state = AgentState(config=config)
        self.load_brief(state)
        self.draft_skeleton(state)
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
        if state.brief is None:
            raise AgentRunError("draft_skeleton requires loaded brief")
        state.game = deterministic_demo_game(state.brief)
        generation = state.game.setdefault("generation", {})
        generation["provider"] = "offline"
        generation["model"] = OFFLINE_MODEL_ID
        generation["agent_graph"] = "v0_27"
        state.add_trace(
            "draft_skeleton",
            "ok",
            "Created deterministic structured game skeleton",
            scenes=len(state.game.get("scenes", [])),
            endings=len(state.game.get("endings", [])),
        )

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
        if state.game is None:
            raise AgentRunError("export_artifacts requires game")
        export_game(state.game, state.config.out_dir)
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
