from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal


Level = Literal["error", "warning"]
ALLOWED_STATUSES = {"open", "acknowledged", "resolved"}
ALLOWED_SEVERITIES = {"info", "minor", "major"}
RISK_FLAG_SEVERITY = {
    "missing_observe_payoff": "major",
    "weak_choice_consequence": "minor",
    "unfair_hidden_information": "major",
    "state_echo_missing": "minor",
    "tone_drift": "minor",
    "none": "info",
}


@dataclass(frozen=True)
class ReviewIssueMessage:
    level: Level
    location: str
    message: str


def build_review_issues(
    project_id: str,
    llm_scene_review: dict[str, Any] | None,
) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    if llm_scene_review and llm_scene_review.get("verdict") == "revise":
        scene_id = llm_scene_review["scene_id"]
        for index, flag in enumerate(llm_scene_review.get("risk_flags", [])):
            if flag == "none":
                continue
            notes = llm_scene_review.get("notes", [])
            issues.append(
                {
                    "id": f"issue_{scene_id}_{flag}_{index + 1}",
                    "source": "llm_scene_review",
                    "scene_id": scene_id,
                    "risk_flag": flag,
                    "severity": RISK_FLAG_SEVERITY.get(flag, "minor"),
                    "status": "open",
                    "summary": notes[index] if index < len(notes) else flag,
                    "blocking": False,
                }
            )
    return {
        "schema_version": "review_issues_v0_1",
        "project_id": project_id,
        "source_review_schema_version": llm_scene_review.get("schema_version") if llm_scene_review else None,
        "issues": issues,
    }


def validate_review_issues(review_issues: dict[str, Any]) -> list[ReviewIssueMessage]:
    messages: list[ReviewIssueMessage] = []
    if review_issues.get("schema_version") != "review_issues_v0_1":
        messages.append(ReviewIssueMessage("error", "schema_version", "Review issues must use review_issues_v0_1"))
    issues = review_issues.get("issues")
    if not isinstance(issues, list):
        messages.append(ReviewIssueMessage("error", "issues", "Issues must be a list"))
        return messages

    seen_ids: set[str] = set()
    for index, issue in enumerate(issues):
        location = f"issues[{index}]"
        if not isinstance(issue, dict):
            messages.append(ReviewIssueMessage("error", location, "Issue must be an object"))
            continue
        issue_id = issue.get("id")
        if not isinstance(issue_id, str) or not issue_id:
            messages.append(ReviewIssueMessage("error", f"{location}.id", "Issue id must be a string"))
        elif issue_id in seen_ids:
            messages.append(ReviewIssueMessage("error", f"{location}.id", f"Duplicate issue id: {issue_id}"))
        else:
            seen_ids.add(issue_id)

        if issue.get("status") not in ALLOWED_STATUSES:
            messages.append(ReviewIssueMessage("error", f"{location}.status", "Issue status is invalid"))
        if issue.get("severity") not in ALLOWED_SEVERITIES:
            messages.append(ReviewIssueMessage("error", f"{location}.severity", "Issue severity is invalid"))
        if not isinstance(issue.get("scene_id"), str) or not issue.get("scene_id"):
            messages.append(ReviewIssueMessage("error", f"{location}.scene_id", "Issue scene_id is required"))
        if not isinstance(issue.get("summary"), str) or not issue.get("summary"):
            messages.append(ReviewIssueMessage("error", f"{location}.summary", "Issue summary is required"))
        if not isinstance(issue.get("blocking"), bool):
            messages.append(ReviewIssueMessage("error", f"{location}.blocking", "Issue blocking must be boolean"))
    return messages
