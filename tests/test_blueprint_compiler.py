from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from gamegen.agent_graph import build_generation_plan, build_state_schema_design
from gamegen.demo_agent import compile_demo_game_from_blueprint, load_brief
from gamegen.scene_blueprint import build_scene_blueprint_design


BRIEF_PATH = ROOT / "examples" / "briefs" / "missing_phone.json"


def valid_brief_and_blueprint() -> tuple[dict, dict]:
  brief = load_brief(BRIEF_PATH)
  plan = build_generation_plan(brief)
  state_schema = build_state_schema_design(brief, plan)
  return brief, build_scene_blueprint_design(brief, plan, state_schema)


class BlueprintCompilerTest(unittest.TestCase):
  def test_compiler_uses_blueprint_scene_order_and_metadata(self) -> None:
    brief, blueprint = valid_brief_and_blueprint()

    game = compile_demo_game_from_blueprint(brief, blueprint)

    self.assertEqual(game["start_scene_id"], blueprint["entry_scene_id"])
    self.assertEqual([scene["id"] for scene in game["scenes"]], [scene["id"] for scene in blueprint["scenes"]])
    self.assertEqual(game["generation"]["draft_source"], "scene_blueprint_demo_library_v0_1")
    self.assertEqual(game["generation"]["compiled_scene_count"], len(blueprint["scenes"]))

  def test_compiler_can_reorder_scene_library_from_blueprint(self) -> None:
    brief, blueprint = valid_brief_and_blueprint()
    reordered = copy.deepcopy(blueprint)
    reordered["scenes"][0], reordered["scenes"][1] = reordered["scenes"][1], reordered["scenes"][0]

    game = compile_demo_game_from_blueprint(brief, reordered)

    self.assertEqual(game["scenes"][0]["id"], reordered["scenes"][0]["id"])
    self.assertEqual(game["scenes"][1]["id"], reordered["scenes"][1]["id"])

  def test_compiler_fails_when_blueprint_references_missing_scene(self) -> None:
    brief, blueprint = valid_brief_and_blueprint()
    broken = copy.deepcopy(blueprint)
    broken["scenes"][0]["id"] = "ch99_missing_scene"

    with self.assertRaisesRegex(ValueError, "ch99_missing_scene"):
      compile_demo_game_from_blueprint(brief, broken)


if __name__ == "__main__":
  unittest.main()
