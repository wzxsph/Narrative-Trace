from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from gamegen.kernel_contract import load_kernel_schemas, validate_kernel_document


FIXTURE_ROOT = ROOT / "examples" / "framework_v1"


class FrameworkV1ContractProofTest(unittest.TestCase):
    def test_all_kernel_schemas_are_valid_draft_2020_12(self) -> None:
        from jsonschema import Draft202012Validator

        schemas = load_kernel_schemas()
        self.assertGreaterEqual(len(schemas), 9)
        for name, schema in schemas.items():
            with self.subTest(schema=name):
                Draft202012Validator.check_schema(schema)

    def test_negotiation_paper_loop_needs_no_kernel_change(self) -> None:
        proof = json.loads((FIXTURE_ROOT / "negotiation_loop_paper.json").read_text(encoding="utf-8"))
        self.assertEqual(proof["required_kernel_changes"], [])
        self.assertEqual(proof["loop_package"]["core_verbs"], ["inspect", "propose", "commit"])
        self.assertEqual(set(proof["kernel_mapping"]), {"state", "surface", "action", "progression", "save", "verification"})
        self.assertEqual(set(proof["extension_namespace"]), {"negotiation"})

    def test_text_to_image_replacement_changes_only_surface_contract(self) -> None:
        fixture_dir = FIXTURE_ROOT / "surface_equivalence"
        text_game = json.loads((fixture_dir / "text_game.json").read_text(encoding="utf-8"))
        image_game = json.loads((fixture_dir / "image_game.json").read_text(encoding="utf-8"))
        registry = json.loads((fixture_dir / "state_registry.json").read_text(encoding="utf-8"))

        self.assertEqual(validate_kernel_document("progression.schema.json", text_game), [])
        self.assertEqual(validate_kernel_document("progression.schema.json", image_game), [])
        self.assertEqual(validate_kernel_document("state.schema.json", registry), [])

        text_without_surface = copy.deepcopy(text_game)
        image_without_surface = copy.deepcopy(image_game)
        text_without_surface["scenes"][0].pop("surfaces")
        image_without_surface["scenes"][0].pop("surfaces")
        self.assertEqual(text_without_surface, image_without_surface)

        text_anchor = text_game["scenes"][0]["surfaces"][0]["anchors"][0]
        image_anchor = image_game["scenes"][0]["surfaces"][0]["anchors"][0]
        for field in ("id", "label", "discoverability", "effects", "unlocks_actions", "fragment"):
            self.assertEqual(text_anchor[field], image_anchor[field])


if __name__ == "__main__":
    unittest.main()
