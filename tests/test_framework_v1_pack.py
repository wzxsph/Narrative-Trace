from __future__ import annotations

import copy
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from gamegen.content_pack import load_content_pack
from gamegen.gates import pack_input_digest, run_g2, run_g3, run_pack_gates
from gamegen.kernel_contract import validate_kernel_document


PACK_ROOT = ROOT / "content_packs" / "missing_phone" / "v1"


class FrameworkV1PackTest(unittest.TestCase):
    def test_migrated_pack_passes_g1_through_g4_with_three_replayable_endings(self) -> None:
        results = run_pack_gates(PACK_ROOT, through="G4")

        self.assertEqual([result.gate_id for result in results], ["G1", "G2", "G3", "G4"])
        self.assertTrue(all(result.status == "passed" for result in results))
        witnesses = results[-1].evidence["ending_witnesses"]
        self.assertEqual(set(witnesses), {"ending_publish", "ending_bury", "ending_confront"})
        self.assertTrue(all(path and path[-1]["kind"] == "action" for path in witnesses.values()))

        repeated = run_pack_gates(PACK_ROOT, through="G4")[-1].evidence["ending_witnesses"]
        self.assertEqual(witnesses, repeated)

    def test_gate_result_uses_closed_kernel_contract(self) -> None:
        for result in run_pack_gates(PACK_ROOT, through="G4"):
            self.assertEqual(validate_kernel_document("gate-result.schema.json", result.to_dict()), [])

    def test_manifest_rejects_unknown_fields_and_multiple_loop_declarations(self) -> None:
        with self.copied_pack() as pack:
            manifest_path = pack / "pack.json"
            manifest = self.read_json(manifest_path)
            manifest["loop_packages"] = [copy.deepcopy(manifest["loop_package"])]
            self.write_json(manifest_path, manifest)

            result = run_pack_gates(pack, through="G1")[0]
            self.assertEqual(result.status, "failed")
            self.assertTrue(any(message.code == "schema.invalid" for message in result.errors))

    def test_loop_version_is_locked_exactly(self) -> None:
        with self.copied_pack() as pack:
            manifest_path = pack / "pack.json"
            manifest = self.read_json(manifest_path)
            manifest["loop_package"]["version"] = "1.0.1"
            self.write_json(manifest_path, manifest)

            result = run_pack_gates(pack, through="G1")[0]
            self.assertEqual(result.status, "failed")
            self.assertTrue(any(message.code == "loop.mismatch" for message in result.errors))

    def test_experimental_pack_requires_visible_notice(self) -> None:
        with self.copied_pack() as pack:
            manifest_path = pack / "pack.json"
            manifest = self.read_json(manifest_path)
            manifest["loop_package"]["tier"] = "experimental"
            manifest["loop_package"]["verification_status"] = "experimental"
            self.write_json(manifest_path, manifest)

            result = run_pack_gates(pack, through="G1")[0]
            self.assertEqual(result.status, "failed")
            self.assertTrue(any(message.code == "schema.invalid" for message in result.errors))

    def test_entrypoint_cannot_escape_pack_root(self) -> None:
        with self.copied_pack() as pack:
            manifest_path = pack / "pack.json"
            manifest = self.read_json(manifest_path)
            manifest["entrypoints"]["game"] = "../../../../generated/missing_phone_v0/game.json"
            self.write_json(manifest_path, manifest)

            result = run_pack_gates(pack, through="G1")[0]
            self.assertEqual(result.status, "failed")
            self.assertEqual(result.errors[0].code, "pack.load")
            self.assertIn("escapes its package root", result.errors[0].message)

    def test_state_registry_is_the_only_initial_state_and_has_no_dead_entries(self) -> None:
        context = load_content_pack(PACK_ROOT)
        self.assertNotIn("initial_state", context.game)
        result = run_g2(context, pack_input_digest(context))
        state_codes = {message.code for message in result.errors if message.code.startswith("state.")}
        self.assertEqual(state_codes, set())

    def test_g2_reports_unregistered_dead_unwritten_and_bad_effect_types(self) -> None:
        context = load_content_pack(PACK_ROOT)
        game = copy.deepcopy(context.game)
        registry = copy.deepcopy(context.state_registry)
        first_action = game["scenes"][0]["actions"][0]
        first_action["requirements"].append({"state": "missing.state", "equals": True})
        first_action["effects"].append({"add": {"clues.voice_note": 1}})
        registry["states"].append(
            {
                "key": "clues.read_only",
                "family": "clue",
                "type": "boolean",
                "initial": False,
                "label": "只读状态",
                "purpose": "测试",
            }
        )
        first_action["requirements"].append({"state": "clues.read_only", "equals": True})
        registry["states"].append(
            {
                "key": "clues.write_only",
                "family": "clue",
                "type": "boolean",
                "initial": False,
                "label": "只写状态",
                "purpose": "测试",
            }
        )
        first_action["effects"].append({"set": {"clues.write_only": True}})
        mutated = copy.copy(context)
        object.__setattr__(mutated, "game", game)
        object.__setattr__(mutated, "state_registry", registry)

        result = run_g2(mutated, pack_input_digest(mutated))
        codes = {message.code for message in result.errors}
        self.assertTrue({"state.unregistered", "state.unwritten", "state.dead", "state.effect_type"} <= codes)

    def test_investigation_depth_is_derived_from_recursive_fragments(self) -> None:
        context = load_content_pack(PACK_ROOT)
        game = copy.deepcopy(context.game)
        root_anchor = game["scenes"][0]["surfaces"][0]["anchors"][0]
        nested_surface = root_anchor["fragment"]["surfaces"][0]
        nested_surface["anchors"] = [copy.deepcopy(root_anchor)]
        nested_surface["anchors"][0]["id"] = "too_deep_anchor"
        nested_surface["anchors"][0]["fragment"]["id"] = "too_deep_fragment"
        mutated = copy.copy(context)
        object.__setattr__(mutated, "game", game)

        result = run_g3(mutated, pack_input_digest(mutated))
        self.assertTrue(any(message.code == "investigation.depth" for message in result.errors))

    @staticmethod
    def read_json(path: Path) -> dict[str, object]:
        return json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def write_json(path: Path, value: object) -> None:
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def copied_pack(self):
        class PackCopy:
            def __init__(self) -> None:
                self.temp = tempfile.TemporaryDirectory()
                self.path = Path(self.temp.name) / "pack"

            def __enter__(self) -> Path:
                shutil.copytree(PACK_ROOT, self.path)
                return self.path

            def __exit__(self, *_: object) -> None:
                self.temp.cleanup()

        return PackCopy()


if __name__ == "__main__":
    unittest.main()
