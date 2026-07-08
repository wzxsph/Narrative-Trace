from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from gamegen.demo_agent import export_game


GAME_PATH = ROOT / "generated" / "missing_phone_v0" / "game.json"


def load_game() -> dict:
  return json.loads(GAME_PATH.read_text(encoding="utf-8"))


class ExportContractTest(unittest.TestCase):
  def test_export_writes_artifacts_after_schema_and_validator_pass(self) -> None:
    with tempfile.TemporaryDirectory() as tmp:
      export_game(load_game(), tmp)
      output = Path(tmp)
      self.assertTrue((output / "game.json").exists())
      self.assertTrue((output / "validation_report.md").exists())
      trace = json.loads((output / "generation_trace.jsonl").read_text(encoding="utf-8"))
      self.assertEqual(trace["schema"], "schemas/game.schema.json")

  def test_export_blocks_invalid_game_before_writing_artifacts(self) -> None:
    game = copy.deepcopy(load_game())
    del game["scenes"][0]["choices"][0]["consequence_level"]

    with tempfile.TemporaryDirectory() as tmp:
      with self.assertRaises(ValueError) as raised:
        export_game(game, tmp)
      self.assertIn("JSON Schema errors", str(raised.exception))
      self.assertFalse((Path(tmp) / "game.json").exists())


if __name__ == "__main__":
  unittest.main()
