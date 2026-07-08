from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from gamegen.agent_graph import build_generation_plan, build_state_schema_design
from gamegen.demo_agent import load_brief
from gamegen.scene_blueprint import build_scene_blueprint_design, validate_scene_blueprint_design


BRIEF_PATH = ROOT / "examples" / "briefs" / "missing_phone.json"


def valid_inputs() -> tuple[dict, dict, dict]:
  brief = load_brief(BRIEF_PATH)
  plan = build_generation_plan(brief)
  state_schema = build_state_schema_design(brief, plan)
  return brief, plan, state_schema


def valid_blueprint() -> tuple[dict, dict, dict]:
  brief, plan, state_schema = valid_inputs()
  return build_scene_blueprint_design(brief, plan, state_schema), plan, state_schema


class SceneBlueprintTest(unittest.TestCase):
  def test_current_scene_blueprint_passes(self) -> None:
    blueprint, plan, state_schema = valid_blueprint()

    messages = validate_scene_blueprint_design(blueprint, plan, state_schema)

    self.assertEqual(messages, [])

  def test_unknown_state_variable_fails(self) -> None:
    blueprint, plan, state_schema = valid_blueprint()
    blueprint["scenes"][0]["state_writes"].append("clues.not_declared")

    messages = validate_scene_blueprint_design(blueprint, plan, state_schema)

    self.assertTrue(any(message.level == "error" and "Unknown state variable: clues.not_declared" == message.message for message in messages))

  def test_unreachable_scene_fails(self) -> None:
    blueprint, plan, state_schema = valid_blueprint()
    blueprint["scenes"][0]["next_scene_ids"] = []

    messages = validate_scene_blueprint_design(blueprint, plan, state_schema)

    self.assertTrue(any(message.level == "error" and "Unreachable scene: ch01_cloud_console" == message.message for message in messages))

  def test_chapter_budget_mismatch_fails(self) -> None:
    blueprint, plan, state_schema = valid_blueprint()
    removed = copy.deepcopy(blueprint["scenes"].pop(2))
    removed["id"] = "ch02_extra_probe"
    removed["chapter_id"] = "ch02"
    blueprint["scenes"].append(removed)

    messages = validate_scene_blueprint_design(blueprint, plan, state_schema)

    self.assertTrue(any(message.level == "error" and "Expected 3 scenes, got 2" == message.message for message in messages))
    self.assertTrue(any(message.level == "error" and "Expected 3 scenes, got 4" == message.message for message in messages))

  def test_ending_coverage_mismatch_fails(self) -> None:
    blueprint, plan, state_schema = valid_blueprint()
    blueprint["scenes"][-1]["ending_targets"] = ["ending_publish"]

    messages = validate_scene_blueprint_design(blueprint, plan, state_schema)

    self.assertTrue(any(message.level == "error" and "Ending target is not covered: ending_bury" == message.message for message in messages))
    self.assertTrue(any(message.level == "error" and "Ending target is not covered: ending_confront" == message.message for message in messages))


if __name__ == "__main__":
  unittest.main()
