from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from gamegen.agent_graph import build_generation_plan, build_state_schema_design
from gamegen.demo_agent import load_brief
from gamegen.state_schema_design import validate_state_schema_design


BRIEF_PATH = ROOT / "examples" / "briefs" / "missing_phone.json"


def valid_design() -> dict:
  brief = load_brief(BRIEF_PATH)
  return build_state_schema_design(brief, build_generation_plan(brief))


class StateSchemaDesignTest(unittest.TestCase):
  def test_current_state_schema_design_passes(self) -> None:
    messages = validate_state_schema_design(valid_design())

    self.assertEqual(messages, [])

  def test_duplicate_variable_key_fails(self) -> None:
    design = valid_design()
    duplicate = copy.deepcopy(design["variables"][0])
    design["variables"].append(duplicate)

    messages = validate_state_schema_design(design)

    self.assertTrue(any(message.level == "error" and "Duplicate variable key" in message.message for message in messages))

  def test_unknown_variable_axis_fails(self) -> None:
    design = valid_design()
    design["variables"][0]["axis"] = "mood"

    messages = validate_state_schema_design(design)

    self.assertTrue(any(message.level == "error" and "Unknown variable axis: mood" == message.message for message in messages))

  def test_relationship_axis_requires_matching_variable(self) -> None:
    design = valid_design()
    design["relationship_axes"]["chen"].append("fear")

    messages = validate_state_schema_design(design)

    self.assertTrue(
      any(
        message.level == "error"
        and message.message == "Declared relationship axis has no variable: relationships.chen.fear"
        for message in messages
      )
    )


if __name__ == "__main__":
  unittest.main()
