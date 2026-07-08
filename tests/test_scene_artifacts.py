from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from gamegen.agent_graph import build_generation_plan, build_state_schema_design
from gamegen.demo_agent import load_brief
from gamegen.scene_artifacts import (
  build_scene_artifacts_from_library,
  compile_game_from_scene_artifacts,
  review_scene_artifacts,
  validate_scene_artifact_release,
  validate_scene_artifacts,
)
from gamegen.scene_blueprint import build_scene_blueprint_design


BRIEF_PATH = ROOT / "examples" / "briefs" / "missing_phone.json"


def valid_inputs() -> tuple[dict, dict, dict]:
  brief = load_brief(BRIEF_PATH)
  plan = build_generation_plan(brief)
  state_schema = build_state_schema_design(brief, plan)
  blueprint = build_scene_blueprint_design(brief, plan, state_schema)
  return brief, blueprint, build_scene_artifacts_from_library(brief, blueprint)


class SceneArtifactsTest(unittest.TestCase):
  def test_scene_artifacts_pass_and_compile_game(self) -> None:
    brief, blueprint, artifacts = valid_inputs()

    messages = validate_scene_artifacts(artifacts, blueprint)
    reviewed = review_scene_artifacts(artifacts)
    release_messages = validate_scene_artifact_release(reviewed)
    game = compile_game_from_scene_artifacts(brief, reviewed)

    self.assertEqual(messages, [])
    self.assertEqual(release_messages, [])
    self.assertEqual(reviewed["schema_version"], "scene_artifacts_v0_1")
    self.assertEqual(reviewed["review_schema_version"], "scene_artifact_review_v0_1")
    self.assertEqual([artifact["scene_id"] for artifact in reviewed["artifacts"]], [scene["id"] for scene in blueprint["scenes"]])
    self.assertEqual([scene["id"] for scene in game["scenes"]], [scene["id"] for scene in blueprint["scenes"]])
    self.assertEqual(game["generation"]["draft_source"], "scene_artifacts_v0_1")
    self.assertTrue(all(artifact["status"] == "locked" for artifact in reviewed["artifacts"]))

  def test_compile_requires_locked_artifacts(self) -> None:
    brief, _, artifacts = valid_inputs()

    with self.assertRaisesRegex(ValueError, "locked"):
      compile_game_from_scene_artifacts(brief, artifacts)

  def test_release_gate_rejects_unapproved_artifact(self) -> None:
    _, _, artifacts = valid_inputs()
    reviewed = review_scene_artifacts(artifacts)
    reviewed["artifacts"][0]["status"] = "draft"

    messages = validate_scene_artifact_release(reviewed)

    self.assertTrue(any(message.level == "error" and message.message == "Artifact must be locked before compile" for message in messages))

  def test_artifact_order_must_match_blueprint(self) -> None:
    _, blueprint, artifacts = valid_inputs()
    artifacts["artifacts"][0], artifacts["artifacts"][1] = artifacts["artifacts"][1], artifacts["artifacts"][0]

    messages = validate_scene_artifacts(artifacts, blueprint)

    self.assertTrue(any(message.level == "error" and message.message == "Artifact scene order must match blueprint scene order" for message in messages))

  def test_artifact_missing_planned_choice_fails(self) -> None:
    _, blueprint, artifacts = valid_inputs()
    broken = copy.deepcopy(artifacts)
    broken["artifacts"][0]["scene"]["choices"] = [
      choice for choice in broken["artifacts"][0]["scene"]["choices"] if choice["id"] != "choice_call_chen"
    ]

    messages = validate_scene_artifacts(broken, blueprint)

    self.assertTrue(any(message.level == "error" and "missing planned choice: choice_call_chen" in message.message for message in messages))

  def test_missing_library_scene_fails_artifact_build(self) -> None:
    brief, blueprint, _ = valid_inputs()
    broken = copy.deepcopy(blueprint)
    broken["scenes"][0]["id"] = "ch99_missing_scene"

    with self.assertRaisesRegex(ValueError, "ch99_missing_scene"):
      build_scene_artifacts_from_library(brief, broken)


if __name__ == "__main__":
  unittest.main()
