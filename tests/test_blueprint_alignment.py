from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from gamegen.agent_graph import build_generation_plan, build_state_schema_design
from gamegen.blueprint_alignment import validate_blueprint_alignment
from gamegen.demo_agent import deterministic_demo_game, load_brief
from gamegen.scene_blueprint import build_scene_blueprint_design


BRIEF_PATH = ROOT / "examples" / "briefs" / "missing_phone.json"


def valid_game_and_blueprint() -> tuple[dict, dict]:
  brief = load_brief(BRIEF_PATH)
  plan = build_generation_plan(brief)
  state_schema = build_state_schema_design(brief, plan)
  return deterministic_demo_game(brief), build_scene_blueprint_design(brief, plan, state_schema)


class BlueprintAlignmentTest(unittest.TestCase):
  def test_current_game_satisfies_scene_blueprint(self) -> None:
    game, blueprint = valid_game_and_blueprint()

    messages = validate_blueprint_alignment(game, blueprint)

    self.assertEqual(messages, [])

  def test_start_scene_must_match_blueprint_entry(self) -> None:
    game, blueprint = valid_game_and_blueprint()
    game["start_scene_id"] = "ch01_cloud_console"

    messages = validate_blueprint_alignment(game, blueprint)

    self.assertTrue(
      any(message.level == "error" and "start_scene_id must match blueprint entry_scene_id" in message.message for message in messages)
    )

  def test_missing_planned_observe_fails(self) -> None:
    game, blueprint = valid_game_and_blueprint()
    first_scene = game["scenes"][0]
    first_scene["background_blocks"][0]["observe_anchors"] = first_scene["background_blocks"][0]["observe_anchors"][1:]

    messages = validate_blueprint_alignment(game, blueprint)

    self.assertTrue(
      any(message.level == "error" and "missing planned observe: obs_unsent_sms" in message.message for message in messages)
    )

  def test_missing_planned_choice_fails(self) -> None:
    game, blueprint = valid_game_and_blueprint()
    first_scene = game["scenes"][0]
    first_scene["choices"] = [choice for choice in first_scene["choices"] if choice["id"] != "choice_call_chen"]

    messages = validate_blueprint_alignment(game, blueprint)

    self.assertTrue(
      any(message.level == "error" and "missing planned choice: choice_call_chen" in message.message for message in messages)
    )

  def test_missing_planned_state_write_fails(self) -> None:
    game, blueprint = valid_game_and_blueprint()
    game = copy.deepcopy(game)
    first_choice = game["scenes"][0]["choices"][0]
    first_choice["effects"] = []

    messages = validate_blueprint_alignment(game, blueprint)

    self.assertTrue(
      any(message.level == "error" and "does not write planned state: relationships.chen.trust" in message.message for message in messages)
    )


if __name__ == "__main__":
  unittest.main()
