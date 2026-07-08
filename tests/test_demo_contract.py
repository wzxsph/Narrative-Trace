from __future__ import annotations

import json
import sys
import unittest
from collections import Counter
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
    self.assertEqual(messages, [])

  def test_deterministic_smoke_path_reaches_publish_ending(self) -> None:
    runtime = SmokeRuntime(load_game())
    runtime.open_anchor("obs_unsent_sms")
    runtime.open_anchor("obs_0213_log")
    runtime.choose("choice_go_station")
    runtime.open_anchor("obs_session_token")
    runtime.choose("choice_freeze_wipe")
    runtime.open_anchor("obs_taxi_order")
    runtime.choose("choice_leave_for_station")
    runtime.open_anchor("obs_station_entry_code")
    runtime.choose("choice_enter_service_corridor")
    runtime.open_anchor("obs_ticket")
    runtime.open_anchor("obs_locker_code")
    runtime.choose("choice_open_locker")
    runtime.open_anchor("obs_backup_drive")
    runtime.choose("choice_take_backup_to_safehouse")
    runtime.open_anchor("obs_raw_recording")
    runtime.choose("choice_compare_context")
    runtime.open_anchor("obs_victim_list")
    runtime.choose("choice_prepare_public_packet")
    runtime.open_anchor("obs_public_packet")
    runtime.choose("choice_publish_truth")
    self.assertEqual(runtime.ending_id, "ending_publish")

  def test_v02_demo_shape_is_three_chapters_with_three_scenes_each(self) -> None:
    game = load_game()
    chapters = Counter(scene["chapter"] for scene in game["scenes"])
    self.assertEqual(game["schema_version"], "game_writer_demo_v0_2")
    self.assertEqual(len(game["scenes"]), 9)
    self.assertEqual(len(chapters), 3)
    self.assertTrue(all(count == 3 for count in chapters.values()))
    self.assertGreaterEqual(len(game["endings"]), 3)
    for scene in game["scenes"]:
      self.assertGreaterEqual(len(scene.get("choices", [])), 2)
      self.assertTrue(
        any(block.get("observe_anchors") for block in scene.get("background_blocks", [])),
        scene["id"],
      )

  def test_every_scene_has_observe_unlocked_action(self) -> None:
    game = load_game()
    for scene in game["scenes"]:
      scene_choice_ids = {choice["id"] for choice in scene["choices"]}
      unlocked = {
        choice_id
        for block in scene["background_blocks"]
        for anchor in flatten_anchors(block["observe_anchors"])
        for choice_id in anchor.get("unlocks_choices", [])
      }
      self.assertTrue(unlocked & scene_choice_ids, scene["id"])

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


def flatten_anchors(anchors: list[dict]) -> list[dict]:
  output = []
  for anchor in anchors:
    output.append(anchor)
    output.extend(flatten_anchors(anchor.get("opens_fragment", {}).get("nested_anchors", [])))
  return output


if __name__ == "__main__":
  unittest.main()
