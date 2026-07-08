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
      self.assertIn("draft_skeleton", nodes)
      self.assertIn("validate_schema", nodes)
      self.assertIn("validate_structure", nodes)
      self.assertIn("validate_content_qa", nodes)
      self.assertIn("repair_if_needed", nodes)
      self.assertIn("export_artifacts", nodes)
      self.assertEqual(nodes[-1], "write_agent_trace")
      repair_events = [event for event in trace if event["node"] == "repair_if_needed"]
      self.assertEqual(repair_events[-1]["status"], "skipped")

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
