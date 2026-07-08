from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from gamegen.validator import validate_game
from scripts.smoke_playthrough import SmokeRuntime


GAME_PATH = ROOT / "generated" / "missing_phone_v0" / "game.json"
APP_JS_PATH = ROOT / "src" / "app.js"


def load_game() -> dict:
  return json.loads(GAME_PATH.read_text(encoding="utf-8"))


class DemoContractTest(unittest.TestCase):
  def test_generated_game_has_no_validation_errors(self) -> None:
    messages = validate_game(load_game())
    errors = [message for message in messages if message.level == "error"]
    self.assertEqual(errors, [])

  def test_deterministic_smoke_path_reaches_publish_ending(self) -> None:
    runtime = SmokeRuntime(load_game())
    runtime.open_anchor("obs_unsent_sms")
    runtime.open_anchor("obs_0213_log")
    runtime.choose("choice_go_station")
    runtime.open_anchor("obs_ticket")
    runtime.open_anchor("obs_locker_code")
    runtime.choose("choice_open_locker")
    runtime.open_anchor("obs_raw_recording")
    runtime.choose("choice_publish_truth")
    self.assertEqual(runtime.ending_id, "ending_publish")

  def test_v0_demo_shape_is_three_chapter_vertical_slice(self) -> None:
    game = load_game()
    chapters = {scene["chapter"] for scene in game["scenes"]}
    self.assertGreaterEqual(len(game["scenes"]), 3)
    self.assertGreaterEqual(len(chapters), 3)
    self.assertGreaterEqual(len(game["endings"]), 3)
    for scene in game["scenes"]:
      self.assertGreaterEqual(len(scene.get("choices", [])), 2)
      self.assertTrue(
        any(block.get("observe_anchors") for block in scene.get("background_blocks", [])),
        scene["id"],
      )

  def test_all_main_endings_are_choice_targets(self) -> None:
    game = load_game()
    ending_ids = {ending["id"] for ending in game["endings"]}
    targets = {
      choice["next_scene"]
      for scene in game["scenes"]
      for choice in scene.get("choices", [])
    }
    self.assertTrue(ending_ids <= targets)

  def test_static_runtime_includes_save_review_and_portrait_hooks(self) -> None:
    app_js = APP_JS_PATH.read_text(encoding="utf-8")
    self.assertIn("SAVE_KEY", app_js)
    self.assertIn("restoreProgress", app_js)
    self.assertIn("renderChapterReview", app_js)
    self.assertIn("buildStateEchoes", app_js)


if __name__ == "__main__":
  unittest.main()
