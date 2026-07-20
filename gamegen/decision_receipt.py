from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from .kernel_contract import canonical_digest, validate_kernel_document


Checkpoint = Literal["brief", "blueprint", "release", "playtest_attribution"]
Decision = Literal["approved", "rejected", "content_issue", "loop_issue", "inconclusive"]


class DecisionReceiptError(ValueError):
    pass


def artifact_digest(path: str | Path) -> str:
    artifact_path = Path(path)
    try:
        value = json.loads(artifact_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise DecisionReceiptError(f"Decision subject not found: {artifact_path}") from exc
    except json.JSONDecodeError as exc:
        raise DecisionReceiptError(f"Decision subject is not valid JSON: {artifact_path}") from exc
    return canonical_digest(value)


def create_decision_receipt(
    *,
    checkpoint: Checkpoint,
    subject_path: str | Path,
    actor: str,
    decision: Decision,
    notes: str = "",
    experimental_opt_in: bool = False,
    decided_at: str | None = None,
) -> dict[str, Any]:
    receipt: dict[str, Any] = {
        "schema_version": "narrative_decision_receipt_v1",
        "checkpoint": checkpoint,
        "subject_digest": artifact_digest(subject_path),
        "decision": decision,
        "actor": actor.strip(),
        "decided_at": decided_at or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "notes": notes,
        "experimental_opt_in": bool(experimental_opt_in),
    }
    errors = validate_kernel_document("decision-receipt.schema.json", receipt)
    if errors:
        raise DecisionReceiptError("Invalid DecisionReceipt: " + "; ".join(errors))
    validate_timestamp(receipt["decided_at"])
    return receipt


def validate_decision_receipt(
    receipt_path: str | Path,
    *,
    checkpoint: Checkpoint,
    subject_path: str | Path,
    allowed_decisions: set[str] | None = None,
    require_experimental_opt_in: bool = False,
) -> dict[str, Any]:
    path = Path(receipt_path)
    try:
        receipt = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise DecisionReceiptError(f"Missing {checkpoint} DecisionReceipt: {path}") from exc
    except json.JSONDecodeError as exc:
        raise DecisionReceiptError(f"Invalid {checkpoint} DecisionReceipt JSON: {path}") from exc
    errors = validate_kernel_document("decision-receipt.schema.json", receipt)
    if errors:
        raise DecisionReceiptError("Invalid DecisionReceipt: " + "; ".join(errors))
    validate_timestamp(receipt["decided_at"])
    if receipt.get("checkpoint") != checkpoint:
        raise DecisionReceiptError(f"Receipt checkpoint is {receipt.get('checkpoint')}, expected {checkpoint}")
    expected_digest = artifact_digest(subject_path)
    if receipt.get("subject_digest") != expected_digest:
        raise DecisionReceiptError(
            f"Stale {checkpoint} DecisionReceipt: subject digest no longer matches the artifact"
        )
    allowed = allowed_decisions or ({"approved"} if checkpoint != "playtest_attribution" else {"content_issue", "loop_issue", "inconclusive"})
    if receipt.get("decision") not in allowed:
        raise DecisionReceiptError(f"Decision '{receipt.get('decision')}' does not permit this transition")
    if require_experimental_opt_in and receipt.get("experimental_opt_in") is not True:
        raise DecisionReceiptError("Experimental loop package requires brief DecisionReceipt opt-in")
    return receipt


def write_receipt(path: str | Path, receipt: dict[str, Any]) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def validate_timestamp(value: str) -> None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, ValueError) as exc:
        raise DecisionReceiptError("DecisionReceipt decided_at must be an ISO 8601 date-time") from exc
    if parsed.tzinfo is None:
        raise DecisionReceiptError("DecisionReceipt decided_at must include a timezone")
