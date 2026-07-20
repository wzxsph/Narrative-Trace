from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from gamegen.content_pack import load_content_pack
from gamegen.decision_receipt import create_decision_receipt, write_receipt
from gamegen.g6 import G6ConfigError, apply_g6_outcome, run_g6
from gamegen.gates import pack_input_digest
from gamegen.kernel_contract import canonical_digest


PACK = ROOT / "content_packs" / "missing_phone" / "v1"
DECIDED_AT = "2026-07-20T14:30:00Z"


def participant(index: int, *, strong: bool = True) -> dict[str, object]:
    completed = strong or index == 4
    path_opened = strong
    return {
        "participant_id": f"p_{index:02d}",
        "consent": True,
        "trace_summary": {
            "duration_seconds": 1200,
            "completed_first_run": completed,
            "chapter1_critical_anchors_found": 4 if strong else (3 if index == 4 else 2),
            "chapter1_critical_anchors_total": 5,
            "blocked_by_hidden_key_anchor": False,
            "path_review_opened": path_opened,
            "ending_id": "ending_publish" if completed else None,
        },
        "interview": {
            "first_minute_understood_expandable_text": strong or index == 4,
            "can_name_observe_unlock_action": strong or index == 4,
            "can_name_action_echo": strong,
            "wants_replay_after_path_review": strong,
            "willing_to_pay_or_recommend": strong,
        },
    }


def valid_batch(batch_id: str = "batch_pass_001") -> dict[str, object]:
    context = load_content_pack(PACK)
    return {
        "schema_version": "investigation_playtest_batch_v1",
        "batch_id": batch_id,
        "loop_package": {"id": "investigation", "version": "1.0.0"},
        "pack_id": context.manifest["pack_id"],
        "pack_version": context.manifest["version"],
        "pack_input_digest": pack_input_digest(context),
        "session_date": "2026-07-20",
        "collection_mode": "local_manual",
        "participants": [participant(index, strong=index <= 3) for index in range(1, 6)],
    }


class FrameworkV1G6Test(unittest.TestCase):
    def test_exact_threshold_batch_passes_and_is_recomputable(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            batch_path = Path(temp) / "batch.json"
            self.write(batch_path, valid_batch())
            result = run_g6(PACK, batch_path)
            self.assertEqual(result.status, "passed")
            self.assertTrue(result.evidence["evaluation_complete"])
            metrics = {item["field"]: item for item in result.evidence["metrics"]}
            self.assertEqual(metrics["completed_first_run"]["value"], 0.8)
            self.assertEqual(metrics["first_minute_understood_expandable_text"]["value"], 0.8)
            self.assertEqual(metrics["can_name_action_echo"]["value"], 0.6)
            self.assertEqual(len(result.evidence["participant_trace_digests"]), 5)
            self.assertEqual(len(result.evidence["participant_record_digests"]), 5)

    def test_invalid_or_nonconsenting_data_cannot_be_tier_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            batch = valid_batch("batch_invalid_001")
            batch["session_date"] = "2026-02-30"
            batch["participants"][0]["consent"] = False  # type: ignore[index]
            batch["participants"][0]["email"] = "not-collected@example.invalid"  # type: ignore[index]
            batch_path = Path(temp) / "batch.json"
            self.write(batch_path, batch)
            result = run_g6(PACK, batch_path)
            self.assertEqual(result.status, "failed")
            self.assertFalse(result.evidence["evaluation_complete"])
            report = Path(temp) / "report.json"
            self.write(report, result.to_dict())
            with self.assertRaisesRegex(G6ConfigError, "Invalid player data"):
                apply_g6_outcome(PACK, batch_path, report)

    def test_metric_failure_requires_digest_bound_attribution(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            batch = valid_batch("batch_fail_001")
            batch["participants"][0]["trace_summary"]["blocked_by_hidden_key_anchor"] = True  # type: ignore[index]
            batch_path = root / "batch.json"
            report_path = root / "g6.json"
            self.write(batch_path, batch)
            result = run_g6(PACK, batch_path)
            self.assertEqual(result.status, "failed")
            self.assertTrue(result.evidence["evaluation_complete"])
            self.write(report_path, result.to_dict())
            with self.assertRaisesRegex(G6ConfigError, "requires a playtest attribution"):
                apply_g6_outcome(PACK, batch_path, report_path)

    def test_pass_clears_debt_and_failure_downgrades_copies(self) -> None:
        for failing in (False, True):
            with self.subTest(failing=failing), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                batch = valid_batch(f"batch_apply_{'fail' if failing else 'pass'}")
                if failing:
                    for item in batch["participants"]:  # type: ignore[index]
                        item["interview"]["willing_to_pay_or_recommend"] = False
                batch_path = root / "batch.json"
                report_path = root / "g6.json"
                loop_path = root / "loop.json"
                pack_path = root / "pack.json"
                self.write(batch_path, batch)
                result = run_g6(PACK, batch_path)
                self.write(report_path, result.to_dict())
                self.write(loop_path, json.loads((ROOT / "loop_packages/investigation/v1/loop.json").read_text()))
                self.write(pack_path, copy.deepcopy(load_content_pack(PACK).manifest))
                receipt_path = None
                if failing:
                    receipt_path = root / "attribution.json"
                    receipt = create_decision_receipt(
                        checkpoint="playtest_attribution",
                        subject_path=report_path,
                        actor="research_owner",
                        decision="inconclusive",
                        notes="Synthetic threshold test only",
                        decided_at=DECIDED_AT,
                    )
                    write_receipt(receipt_path, receipt)
                applied = apply_g6_outcome(
                    PACK,
                    batch_path,
                    report_path,
                    attribution_receipt=receipt_path,
                    loop_manifest_path=loop_path,
                    dependent_pack_manifests=[pack_path],
                )
                loop = json.loads(loop_path.read_text())
                pack = json.loads(pack_path.read_text())
                expected = "experimental" if failing else "verified"
                self.assertEqual(applied["status"], expected)
                self.assertEqual(loop["verification"]["status"], expected)
                self.assertEqual(pack["loop_package"]["verification_status"], expected)
                self.assertEqual(pack["experimental_notice"], failing)
                self.assertEqual(loop["verification"]["evidence"][-1]["digest"], canonical_digest(result.to_dict()))
                if failing:
                    self.assertEqual(loop["verification"]["evidence"][-1]["attribution"], "inconclusive")

    def test_cli_exit_codes_are_stable(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            batch_path = root / "batch.json"
            report_path = root / "report.json"
            self.write(batch_path, valid_batch("batch_cli_001"))
            passed = subprocess.run(
                [
                    sys.executable,
                    "scripts/evaluate_g6.py",
                    "evaluate",
                    "--pack",
                    str(PACK),
                    "--batch",
                    str(batch_path),
                    "--out",
                    str(report_path),
                ],
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(passed.returncode, 0, passed.stderr)
            failed_batch = valid_batch("batch_cli_fail_001")
            failed_batch["participants"][0]["trace_summary"]["blocked_by_hidden_key_anchor"] = True  # type: ignore[index]
            self.write(batch_path, failed_batch)
            failed = subprocess.run(
                [
                    sys.executable,
                    "scripts/evaluate_g6.py",
                    "evaluate",
                    "--pack",
                    str(PACK),
                    "--batch",
                    str(batch_path),
                    "--out",
                    str(report_path),
                ],
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(failed.returncode, 1, failed.stderr)
            config_error = subprocess.run(
                [
                    sys.executable,
                    "scripts/evaluate_g6.py",
                    "evaluate",
                    "--pack",
                    str(PACK),
                    "--batch",
                    str(root / "missing.json"),
                    "--out",
                    str(report_path),
                ],
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(config_error.returncode, 2)

    @staticmethod
    def write(path: Path, value: object) -> None:
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
