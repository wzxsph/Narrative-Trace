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

  def test_v05_demo_shape_is_three_chapters_with_three_scenes_each(self) -> None:
    game = load_game()
    chapters = Counter(scene["chapter"] for scene in game["scenes"])
    self.assertEqual(game["schema_version"], "game_writer_demo_v0_5")
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

  def test_first_chapter_includes_diegetic_guidance(self) -> None:
    game = load_game()
    first_scene = next(scene for scene in game["scenes"] if scene["id"] == "ch01_phone_lock")
    anchors = {
      anchor["id"]: anchor
      for block in first_scene["background_blocks"]
      for anchor in flatten_anchors(block["observe_anchors"])
    }

    first_observe = anchors["obs_unsent_sms"].get("guidance", {})
    choice_unlock = anchors["obs_0213_log"].get("unlock_guidance", {})
    self.assertEqual(first_observe.get("id"), "guide_first_observe")
    self.assertTrue(first_observe.get("title"))
    self.assertTrue(first_observe.get("text"))
    self.assertEqual(choice_unlock.get("id"), "guide_choice_from_observe")
    self.assertTrue(choice_unlock.get("title"))
    self.assertTrue(choice_unlock.get("text"))

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

  def test_relationship_state_echoes_have_longitudinal_coverage(self) -> None:
    game = load_game()
    echo_scenes_by_state: dict[str, set[str]] = {}
    for scene in game["scenes"]:
      for echo in scene.get("state_echoes", []):
        self.assertTrue(echo.get("text"), echo.get("id"))
        for requirement in echo.get("requirements", []):
          state = requirement.get("state", "")
          if state.startswith("relationships."):
            echo_scenes_by_state.setdefault(state, set()).add(scene["id"])

    self.assertGreaterEqual(len(echo_scenes_by_state.get("relationships.chen.trust", set())), 2)
    self.assertGreaterEqual(len(echo_scenes_by_state.get("relationships.chen.suspicion", set())), 2)
    self.assertGreaterEqual(len(echo_scenes_by_state.get("relationships.lin.bond", set())), 2)

  def test_static_runtime_includes_save_review_and_portrait_hooks(self) -> None:
    app_js = APP_JS_PATH.read_text(encoding="utf-8")
    self.assertIn("SAVE_KEY", app_js)
    self.assertIn("SAVE_VERSION = 2", app_js)
    self.assertIn("restoreProgress", app_js)
    self.assertIn("migrateSavePayload", app_js)
    self.assertIn("recoveryNotice", app_js)
    self.assertIn("renderRecoveryNotice", app_js)
    self.assertIn("save-recovery", app_js)
    self.assertIn("activeGuidance", app_js)
    self.assertIn("renderGuidance", app_js)
    self.assertIn("newly-unlocked", app_js)
    self.assertIn("renderChapterReview", app_js)
    self.assertIn("renderChapterFlow", app_js)
    self.assertIn("buildChoiceBranchState", app_js)
    self.assertIn("describeRequirement", app_js)
    self.assertIn("syncPathPanelAccessibility", app_js)
    self.assertIn("aria-expanded", app_js)
    self.assertIn("inert", app_js)
    self.assertIn("dataset.anchorId", app_js)
    self.assertIn("dataset.choiceId", app_js)
    self.assertIn("continue-review", app_js)
    self.assertIn("未解锁：", app_js)
    self.assertIn("chapter-flow-node", app_js)
    self.assertIn("renderStateEchoes", app_js)
    self.assertIn("buildStateEchoes", app_js)

  def test_browser_e2e_matrix_covers_all_main_endings(self) -> None:
    from scripts.browser_e2e_matrix import PATHS

    game = load_game()
    expected_endings = {ending["id"] for ending in game["endings"]}
    matrix_endings = {path.expected_ending for path in PATHS}
    self.assertEqual(matrix_endings, expected_endings)
    for path in PATHS:
      self.assertTrue(any(step.kind == "observe" for step in path.steps), path.name)
      self.assertTrue(any(step.kind == "choice" for step in path.steps), path.name)


def flatten_anchors(anchors: list[dict]) -> list[dict]:
  output = []
  for anchor in anchors:
    output.append(anchor)
    output.extend(flatten_anchors(anchor.get("opens_fragment", {}).get("nested_anchors", [])))
  return output


if __name__ == "__main__":
  unittest.main()
