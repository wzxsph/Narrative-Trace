from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from gamegen.schema_contract import validate_against_schema


GAME_PATH = ROOT / "generated" / "missing_phone_v0" / "game.json"
SCHEMA_PATH = ROOT / "schemas" / "game.schema.json"


def load_json(path: Path) -> dict:
  return json.loads(path.read_text(encoding="utf-8"))


class JsonSchemaContractTest(unittest.TestCase):
  def setUp(self) -> None:
    self.game = load_json(GAME_PATH)
    self.schema = load_json(SCHEMA_PATH)

  def test_current_generated_game_matches_json_schema(self) -> None:
    self.assertEqual(validate_against_schema(self.game, self.schema), [])

  def test_missing_required_scene_field_fails_schema(self) -> None:
    game = copy.deepcopy(self.game)
    del game["scenes"][0]["background_blocks"]

    errors = validate_against_schema(game, self.schema)
    self.assertTrue(any("background_blocks" in error for error in errors))

  def test_invalid_choice_consequence_level_fails_schema(self) -> None:
    game = copy.deepcopy(self.game)
    game["scenes"][0]["choices"][0]["consequence_level"] = "cosmetic"

    errors = validate_against_schema(game, self.schema)
    self.assertTrue(any("consequence_level" in error for error in errors))

  def test_observe_fragment_requires_nested_anchors_array(self) -> None:
    game = copy.deepcopy(self.game)
    fragment = game["scenes"][0]["background_blocks"][0]["observe_anchors"][0]["opens_fragment"]
    del fragment["nested_anchors"]

    errors = validate_against_schema(game, self.schema)
    self.assertTrue(any("nested_anchors" in error for error in errors))


if __name__ == "__main__":
  unittest.main()
