from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from gamegen.validator import validate_game
from scripts.repair_game import repair_game


GAME_PATH = ROOT / "generated" / "missing_phone_v0" / "game.json"


def load_game() -> dict:
  return json.loads(GAME_PATH.read_text(encoding="utf-8"))


def validation_errors(game: dict) -> list[str]:
  return [message.message for message in validate_game(game) if message.level == "error"]


class RepairGameTest(unittest.TestCase):
  def test_repairs_common_local_generation_errors(self) -> None:
    game = copy.deepcopy(load_game())
    game["start_scene_id"] = "missing_start_scene"
    game["scenes"][0]["choices"][0]["next_scene"] = "ch01_cloud_consol"

    first_block = game["scenes"][0]["background_blocks"][0]
    first_block["text"] = first_block["text"].replace("未发送短信", "短信草稿")
    first_anchor = first_block["observe_anchors"][0]
    first_anchor["depth"] = 2
    nested_anchor = first_anchor["opens_fragment"]["nested_anchors"][0]
    nested_anchor["unlocks_choices"] = ["choice_go_statio"]

    self.assertTrue(validation_errors(game))
    repaired, repairs = repair_game(game)

    self.assertTrue(repairs)
    self.assertEqual(validation_errors(repaired), [])
    self.assertEqual(repaired["start_scene_id"], "ch01_phone_lock")
    self.assertEqual(repaired["scenes"][0]["choices"][0]["next_scene"], "ch01_cloud_console")
    self.assertIn("未发送短信", repaired["scenes"][0]["background_blocks"][0]["text"])
    self.assertEqual(repaired["scenes"][0]["background_blocks"][0]["observe_anchors"][0]["depth"], 1)
    fixed_nested = repaired["scenes"][0]["background_blocks"][0]["observe_anchors"][0]["opens_fragment"]["nested_anchors"][0]
    self.assertEqual(fixed_nested["unlocks_choices"], ["choice_go_station"])

  def test_removes_unrepairable_unlock_choice_reference(self) -> None:
    game = copy.deepcopy(load_game())
    game["scenes"][0]["background_blocks"][0]["observe_anchors"][0]["unlocks_choices"] = ["totally_missing_choice"]

    repaired, repairs = repair_game(game)

    self.assertTrue(any("removed invalid choice id" in item for item in repairs))
    self.assertEqual(repaired["scenes"][0]["background_blocks"][0]["observe_anchors"][0]["unlocks_choices"], [])
    self.assertEqual(validation_errors(repaired), [])


if __name__ == "__main__":
  unittest.main()
