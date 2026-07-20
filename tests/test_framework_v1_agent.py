from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from gamegen.content_pack import load_content_pack
from gamegen.gates import GateResult, pack_input_digest, run_pack_gates
from gamegen.v1_agent import (
    V1AgentError,
    advance_pipeline,
    approve_pipeline_checkpoint,
    build_release_bundle,
    prepare_pipeline,
)


BRIEF = ROOT / "examples" / "briefs" / "missing_phone.json"
DECIDED_AT = "2026-07-20T12:00:00Z"


class FrameworkV1AgentTest(unittest.TestCase):
    def test_pipeline_pauses_at_brief_and_blueprint_receipts(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            pipeline = prepare_pipeline(BRIEF, root, provider="offline")
            self.assertEqual(pipeline["phase"], "awaiting_brief_approval")
            self.assertFalse((root / "artifacts" / "scene_artifacts.json").exists())
            with self.assertRaisesRegex(V1AgentError, "Missing brief DecisionReceipt"):
                advance_pipeline(root)

            self.approve(root, "brief")
            pipeline = advance_pipeline(root)
            self.assertEqual(pipeline["phase"], "awaiting_blueprint_approval")
            self.assertTrue((root / "artifacts" / "scene_blueprint.json").exists())
            self.assertFalse((root / "artifacts" / "scene_artifacts.json").exists())
            self.assertFalse((root / "pack.json").exists())
            with self.assertRaisesRegex(V1AgentError, "Missing blueprint DecisionReceipt"):
                advance_pipeline(root)

    def test_stale_receipt_and_experimental_without_opt_in_are_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            prepare_pipeline(BRIEF, root, provider="offline")
            self.approve(root, "brief")
            brief_path = root / "artifacts" / "brief.json"
            brief = self.read_json(brief_path)
            brief["brief"]["project"]["title"] = "changed after approval"
            self.write_json(brief_path, brief)
            with self.assertRaisesRegex(V1AgentError, "Stale brief DecisionReceipt"):
                advance_pipeline(root)

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            prepare_pipeline(BRIEF, root, provider="offline")
            pipeline_path = root / "pipeline.json"
            pipeline = self.read_json(pipeline_path)
            pipeline["loop_package"]["tier"] = "experimental"
            pipeline["loop_package"]["verification_status"] = "experimental"
            self.write_json(pipeline_path, pipeline)
            self.approve(root, "brief", experimental_opt_in=False)
            with self.assertRaisesRegex(V1AgentError, "requires brief DecisionReceipt opt-in"):
                advance_pipeline(root)

    def test_offline_generation_is_deterministic_and_provenance_complete(self) -> None:
        digests: list[str] = []
        for _ in range(2):
            with tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                self.stage_through_blueprint(root)
                pipeline = advance_pipeline(root, gate_through="G4")
                self.assertEqual(pipeline["phase"], "gates_incomplete")
                results = run_pack_gates(root, through="G4")
                self.assertEqual([result.status for result in results], ["passed"] * 4)
                context = load_content_pack(root)
                digests.append(pack_input_digest(context))
                self.assertTrue((root / "compat" / "v0" / "game.json").exists())
                self.assertTrue((root / "compat" / "v0" / "DEPRECATED.md").exists())
                provenance_paths = {item["path"] for item in context.provenance["artifacts"]}
                self.assertIn("artifacts/scene_blueprint.json", provenance_paths)
                self.assertIn("artifacts/scene_artifacts.json", provenance_paths)
                self.assertIn("decisions/brief.json", provenance_paths)
                self.assertIn("decisions/blueprint.json", provenance_paths)
                provenance_text = json.dumps(context.provenance, ensure_ascii=False)
                self.assertNotIn(str(root), provenance_text)
                self.assertNotIn("LLM_API_KEY", (root / "artifacts" / "agent_trace.jsonl").read_text(encoding="utf-8"))
        self.assertEqual(digests[0], digests[1])

    def test_release_bundle_requires_current_release_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as temp, tempfile.TemporaryDirectory() as bundle_temp:
            root = Path(temp)
            self.stage_through_blueprint(root)
            advance_pipeline(root, gate_through="G4")
            passed = [GateResult(gate, "0" * 64).finish() for gate in ("G1", "G2", "G3", "G4", "G5")]
            with mock.patch("gamegen.v1_agent.run_pack_gates", return_value=passed):
                pipeline = advance_pipeline(root, gate_through="G5")
            self.assertEqual(pipeline["phase"], "awaiting_release_approval")
            with self.assertRaisesRegex(V1AgentError, "Missing release DecisionReceipt"):
                build_release_bundle(root, Path(bundle_temp) / "site")

            self.approve(root, "release")
            candidate_path = root / "artifacts" / "release_candidate.json"
            candidate = self.read_json(candidate_path)
            candidate["status"] = "changed_after_approval"
            self.write_json(candidate_path, candidate)
            with self.assertRaisesRegex(V1AgentError, "Stale release DecisionReceipt"):
                build_release_bundle(root, Path(bundle_temp) / "site")

    def test_receipt_rejects_secret_shaped_actor_and_legacy_cli_warns(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            prepare_pipeline(BRIEF, root, provider="offline")
            with self.assertRaisesRegex(V1AgentError, "sensitive data"):
                approve_pipeline_checkpoint(
                    root,
                    "brief",
                    actor="sk-this_should_never_be_logged",
                    decided_at=DECIDED_AT,
                )

        with tempfile.TemporaryDirectory() as temp:
            completed = subprocess.run(
                [
                    sys.executable,
                    "scripts/run_generation_agent.py",
                    "--brief",
                    str(BRIEF),
                    "--out",
                    temp,
                    "--provider",
                    "offline",
                ],
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertIn("DEPRECATED", completed.stderr)
            self.assertTrue((Path(temp) / "game.json").exists())

    def stage_through_blueprint(self, root: Path) -> None:
        prepare_pipeline(BRIEF, root, provider="offline")
        self.approve(root, "brief")
        advance_pipeline(root)
        self.approve(root, "blueprint")

    @staticmethod
    def approve(root: Path, checkpoint: str, experimental_opt_in: bool = False) -> None:
        approve_pipeline_checkpoint(
            root,
            checkpoint,
            actor="test_operator",
            notes="test approval",
            experimental_opt_in=experimental_opt_in,
            decided_at=DECIDED_AT,
        )

    @staticmethod
    def read_json(path: Path) -> dict[str, object]:
        return json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def write_json(path: Path, value: object) -> None:
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
