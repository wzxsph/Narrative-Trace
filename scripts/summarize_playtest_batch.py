from __future__ import annotations

import json
import sys
from pathlib import Path
from statistics import mean
from typing import Any


SCHEMA_VERSION = "game_writer_playtest_batch_v0_1"

BOOLEAN_FIELDS = [
    "first_minute_understood_expandable_text",
    "can_name_observe_unlock_choice",
    "can_name_choice_echo",
    "opened_path_map_and_wants_replay",
    "blocked_by_hidden_key_point",
]

METRIC_LABELS = {
    "first_minute_understood_expandable_text": "80% 第一分钟理解文字可以展开",
    "chapter1_key_observe_found_ratio": "70% 第一章发现至少 60% 关键 observe",
    "can_name_observe_unlock_choice": "70% 能说出 observe 解锁 choice 例子",
    "can_name_choice_echo": "60% 能说出选择的后续影响",
    "opened_path_map_and_wants_replay": "50% 愿意查看路径图并表达重玩意愿",
    "blocked_by_hidden_key_point": "0 人因关键隐藏点不可发现而卡死",
}


def load_batch(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def evaluate_batch(batch: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    errors = validate_batch(batch)
    participants = batch.get("participants", [])
    if errors:
        return {"overall_pass": False, "metrics": []}, errors

    count = len(participants)
    metrics = [
        build_boolean_metric(
            participants,
            "first_minute_understood_expandable_text",
            threshold=0.8,
            greater_is_better=True,
        ),
        build_ratio_floor_metric(
            participants,
            "chapter1_key_observe_found_ratio",
            participant_floor=0.6,
            threshold=0.7,
        ),
        build_boolean_metric(
            participants,
            "can_name_observe_unlock_choice",
            threshold=0.7,
            greater_is_better=True,
        ),
        build_boolean_metric(
            participants,
            "can_name_choice_echo",
            threshold=0.6,
            greater_is_better=True,
        ),
        build_boolean_metric(
            participants,
            "opened_path_map_and_wants_replay",
            threshold=0.5,
            greater_is_better=True,
        ),
        build_blocked_metric(participants),
    ]
    overall_pass = all(metric["pass"] for metric in metrics)
    durations = [item["duration_minutes"] for item in participants if item.get("duration_minutes", 0) > 0]
    return {
        "participant_count": count,
        "average_duration_minutes": round(mean(durations), 1) if durations else 0,
        "overall_pass": overall_pass,
        "metrics": metrics,
    }, []


def validate_batch(batch: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if batch.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version must be {SCHEMA_VERSION}")
    participants = batch.get("participants")
    if not isinstance(participants, list) or not participants:
        errors.append("participants must be a non-empty list")
        return errors

    for index, participant in enumerate(participants, start=1):
        prefix = f"participants[{index}]"
        if not participant.get("id"):
            errors.append(f"{prefix}.id is required")
        duration = participant.get("duration_minutes")
        if not isinstance(duration, (int, float)) or duration < 0:
            errors.append(f"{prefix}.duration_minutes must be a non-negative number")
        for field in BOOLEAN_FIELDS:
            if not isinstance(participant.get(field), bool):
                errors.append(f"{prefix}.{field} must be true or false")
        ratio = participant.get("chapter1_key_observe_found_ratio")
        if not isinstance(ratio, (int, float)) or ratio < 0 or ratio > 1:
            errors.append(f"{prefix}.chapter1_key_observe_found_ratio must be between 0 and 1")
    return errors


def build_boolean_metric(
    participants: list[dict[str, Any]],
    field: str,
    threshold: float,
    greater_is_better: bool,
) -> dict[str, Any]:
    true_count = sum(1 for item in participants if item[field])
    ratio = true_count / len(participants)
    passed = ratio >= threshold if greater_is_better else ratio <= threshold
    return {
        "field": field,
        "label": METRIC_LABELS[field],
        "value": round(ratio, 3),
        "threshold": threshold,
        "pass": passed,
    }


def build_ratio_floor_metric(
    participants: list[dict[str, Any]],
    field: str,
    participant_floor: float,
    threshold: float,
) -> dict[str, Any]:
    qualified_count = sum(1 for item in participants if item[field] >= participant_floor)
    ratio = qualified_count / len(participants)
    return {
        "field": field,
        "label": METRIC_LABELS[field],
        "value": round(ratio, 3),
        "threshold": threshold,
        "participant_floor": participant_floor,
        "pass": ratio >= threshold,
    }


def build_blocked_metric(participants: list[dict[str, Any]]) -> dict[str, Any]:
    blocked_count = sum(1 for item in participants if item["blocked_by_hidden_key_point"])
    return {
        "field": "blocked_by_hidden_key_point",
        "label": METRIC_LABELS["blocked_by_hidden_key_point"],
        "value": blocked_count,
        "threshold": 0,
        "pass": blocked_count == 0,
    }


def format_report(summary: dict[str, Any], errors: list[str]) -> str:
    if errors:
        lines = ["# Playtest Batch Report", "", "Status: INVALID", ""]
        lines.extend(f"- {error}" for error in errors)
        return "\n".join(lines)

    lines = [
        "# Playtest Batch Report",
        "",
        f"Participants: {summary['participant_count']}",
        f"Average duration minutes: {summary['average_duration_minutes']}",
        f"Overall: {'PASS' if summary['overall_pass'] else 'FAIL'}",
        "",
        "## Metrics",
        "",
    ]
    for metric in summary["metrics"]:
        status = "PASS" if metric["pass"] else "FAIL"
        lines.append(f"- {status}: {metric['label']} = {metric['value']} / threshold {metric['threshold']}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if len(args) != 1:
        print("Usage: python3 scripts/summarize_playtest_batch.py <playtest_batch.json>")
        return 2
    batch = load_batch(args[0])
    summary, errors = evaluate_batch(batch)
    print(format_report(summary, errors))
    if errors:
        return 1
    return 0 if summary["overall_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
