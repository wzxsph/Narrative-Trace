from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from gamegen.agent_graph import AgentConfig, AgentState, GenerationAgentGraph, run_generation_agent
from gamegen.demo_agent import load_brief, deterministic_demo_game


BRIEF_PATH = ROOT / "examples" / "briefs" / "missing_phone.json"


class AgentGraphTest(unittest.TestCase):
  def test_offline_agent_exports_artifacts_and_trace(self) -> None:
    with tempfile.TemporaryDirectory() as tmp:
      state = run_generation_agent(BRIEF_PATH, tmp, provider="offline")
      output = Path(tmp)

      self.assertTrue(state.exported)
      self.assertEqual(state.repair_attempts, 0)
      self.assertTrue((output / "game.json").exists())
      self.assertTrue((output / "game.yaml").exists())
      self.assertTrue((output / "generation_plan.json").exists())
      self.assertTrue((output / "state_schema_design.json").exists())
      self.assertTrue((output / "scene_blueprint.json").exists())
      self.assertTrue((output / "scene_artifacts.json").exists())
      self.assertTrue((output / "review_issues.json").exists())
      self.assertTrue((output / "review_issue_policy.json").exists())
      self.assertTrue((output / "path_map.json").exists())
      self.assertTrue((output / "state_registry.json").exists())
      self.assertTrue((output / "validation_report.md").exists())
      self.assertTrue((output / "generation_trace.jsonl").exists())
      self.assertTrue((output / "agent_trace.jsonl").exists())

      trace = [
        json.loads(line)
        for line in (output / "agent_trace.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
      ]
      nodes = [event["node"] for event in trace]
      self.assertEqual(nodes[0], "load_brief")
      self.assertIn("plan_story_structure", nodes)
      self.assertIn("design_state_schema", nodes)
      self.assertIn("validate_state_schema_design", nodes)
      self.assertIn("design_scene_blueprint", nodes)
      self.assertIn("validate_scene_blueprint", nodes)
      self.assertIn("draft_scene_artifacts", nodes)
      self.assertIn("validate_scene_artifacts", nodes)
      self.assertIn("optional_llm_scene_review", nodes)
      self.assertIn("build_review_issues", nodes)
      self.assertIn("validate_review_issues", nodes)
      self.assertIn("evaluate_review_issue_release_policy", nodes)
      self.assertIn("validate_review_issue_release_policy", nodes)
      self.assertIn("review_scene_artifacts", nodes)
      self.assertIn("validate_scene_artifact_release", nodes)
      self.assertIn("draft_skeleton", nodes)
      self.assertIn("validate_blueprint_alignment", nodes)
      self.assertIn("validate_schema", nodes)
      self.assertIn("validate_structure", nodes)
      self.assertIn("validate_content_qa", nodes)
      self.assertIn("repair_if_needed", nodes)
      self.assertIn("export_artifacts", nodes)
      self.assertEqual(nodes[-1], "write_agent_trace")
      repair_events = [event for event in trace if event["node"] == "repair_if_needed"]
      self.assertEqual(repair_events[-1]["status"], "skipped")
      draft_events = [event for event in trace if event["node"] == "draft_skeleton"]
      self.assertEqual(draft_events[-1]["metrics"]["draft_source"], "scene_artifacts_v0_1")
      self.assertEqual(draft_events[-1]["metrics"]["locked_scene_artifacts"], 9)

      generation_plan = json.loads((output / "generation_plan.json").read_text(encoding="utf-8"))
      self.assertEqual(generation_plan["plan_schema_version"], "generation_plan_v0_1")
      self.assertEqual(generation_plan["project_id"], "missing_phone")
      self.assertEqual(generation_plan["chapter_count"], 3)
      self.assertEqual(generation_plan["scene_count"], 9)
      self.assertEqual(len(generation_plan["chapters"]), 3)
      self.assertEqual(len(generation_plan["ending_targets"]), 3)

      state_schema = json.loads((output / "state_schema_design.json").read_text(encoding="utf-8"))
      self.assertEqual(state_schema["schema_version"], "state_schema_design_v0_1")
      self.assertEqual(state_schema["project_id"], "missing_phone")
      self.assertEqual({axis["id"] for axis in state_schema["axes"]}, {"clues", "stance", "relationships", "pressure"})
      self.assertEqual(state_schema["relationship_axes"]["chen"], ["trust", "suspicion"])
      self.assertGreaterEqual(len(state_schema["variables"]), 16)
      variable_keys = {variable["key"] for variable in state_schema["variables"]}
      self.assertIn("relationships.chen.trust", variable_keys)
      self.assertIn("relationships.lin.bond", variable_keys)
      self.assertIn("pressure.company_alert", variable_keys)

      state_schema_events = [event for event in trace if event["node"] == "validate_state_schema_design"]
      self.assertEqual(state_schema_events[-1]["status"], "ok")

      scene_blueprint = json.loads((output / "scene_blueprint.json").read_text(encoding="utf-8"))
      self.assertEqual(scene_blueprint["schema_version"], "scene_blueprint_v0_1")
      self.assertEqual(scene_blueprint["entry_scene_id"], "ch01_phone_lock")
      self.assertEqual(len(scene_blueprint["scenes"]), 9)
      self.assertEqual(scene_blueprint["ending_targets"], generation_plan["ending_targets"])
      scene_blueprint_events = [event for event in trace if event["node"] == "validate_scene_blueprint"]
      self.assertEqual(scene_blueprint_events[-1]["status"], "ok")
      scene_artifact_events = [event for event in trace if event["node"] == "validate_scene_artifacts"]
      self.assertEqual(scene_artifact_events[-1]["status"], "ok")
      llm_scene_review_events = [event for event in trace if event["node"] == "optional_llm_scene_review"]
      self.assertEqual(llm_scene_review_events[-1]["status"], "skipped")
      review_issue_events = [event for event in trace if event["node"] == "validate_review_issues"]
      self.assertEqual(review_issue_events[-1]["status"], "ok")
      policy_events = [event for event in trace if event["node"] == "validate_review_issue_release_policy"]
      self.assertEqual(policy_events[-1]["status"], "ok")
      release_events = [event for event in trace if event["node"] == "validate_scene_artifact_release"]
      self.assertEqual(release_events[-1]["status"], "ok")
      alignment_events = [event for event in trace if event["node"] == "validate_blueprint_alignment"]
      self.assertEqual(alignment_events[-1]["status"], "ok")

      scene_artifacts = json.loads((output / "scene_artifacts.json").read_text(encoding="utf-8"))
      self.assertEqual(scene_artifacts["schema_version"], "scene_artifacts_v0_1")
      self.assertEqual(scene_artifacts["review_schema_version"], "scene_artifact_review_v0_1")
      self.assertEqual(len(scene_artifacts["artifacts"]), 9)
      self.assertTrue(all(artifact["status"] == "locked" for artifact in scene_artifacts["artifacts"]))

      review_issues = json.loads((output / "review_issues.json").read_text(encoding="utf-8"))
      self.assertEqual(review_issues["schema_version"], "review_issues_v0_1")
      self.assertEqual(review_issues["issues"], [])
      review_policy = json.loads((output / "review_issue_policy.json").read_text(encoding="utf-8"))
      self.assertEqual(review_policy["schema_version"], "review_issue_release_policy_v0_1")
      self.assertEqual(review_policy["status"], "passed")

  def test_repair_node_applies_supported_structural_repairs(self) -> None:
    brief = load_brief(BRIEF_PATH)
    game = deterministic_demo_game(brief)
    broken_game = copy.deepcopy(game)
    broken_game["start_scene_id"] = "missing_scene"

    with tempfile.TemporaryDirectory() as tmp:
      state = AgentState(
        config=AgentConfig(
          brief_path=BRIEF_PATH,
          out_dir=Path(tmp),
          provider="offline",
          max_repair_attempts=1,
        ),
        brief=brief,
        game=broken_game,
      )
      GenerationAgentGraph().repair_if_needed(state)

      self.assertEqual(state.repair_attempts, 1)
      self.assertTrue(state.repairs)
      self.assertEqual(state.game["start_scene_id"], "ch01_phone_lock")
      self.assertEqual(state.trace_events[-1].node, "repair_if_needed")
      self.assertEqual(state.trace_events[-1].status, "ok")


if __name__ == "__main__":
  unittest.main()
