from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.summarize_playtest_batch import evaluate_batch, format_report


TEMPLATE_PATH = ROOT / "examples" / "playtests" / "internal_playtest_batch_template.json"


def participant(**overrides: object) -> dict[str, object]:
  data: dict[str, object] = {
    "id": "p",
    "duration_minutes": 18,
    "first_minute_understood_expandable_text": True,
    "chapter1_key_observe_found_ratio": 0.7,
    "can_name_observe_unlock_choice": True,
    "can_name_choice_echo": True,
    "opened_path_map_and_wants_replay": True,
    "blocked_by_hidden_key_point": False,
  }
  data.update(overrides)
  return data


class PlaytestSummaryTest(unittest.TestCase):
  def test_batch_passes_when_prd_thresholds_are_met(self) -> None:
    batch = {
      "schema_version": "game_writer_playtest_batch_v0_1",
      "participants": [
        participant(id="p01"),
        participant(id="p02"),
        participant(id="p03"),
        participant(id="p04", can_name_choice_echo=False),
        participant(
          id="p05",
          first_minute_understood_expandable_text=False,
          chapter1_key_observe_found_ratio=0.4,
          can_name_observe_unlock_choice=False,
          can_name_choice_echo=False,
          opened_path_map_and_wants_replay=False,
        ),
      ],
    }

    summary, errors = evaluate_batch(batch)
    self.assertEqual(errors, [])
    self.assertTrue(summary["overall_pass"])
    self.assertIn("Overall: PASS", format_report(summary, errors))

  def test_batch_fails_when_any_player_is_blocked_by_hidden_key_point(self) -> None:
    batch = {
      "schema_version": "game_writer_playtest_batch_v0_1",
      "participants": [
        participant(id="p01"),
        participant(id="p02", blocked_by_hidden_key_point=True),
      ],
    }

    summary, errors = evaluate_batch(batch)
    self.assertEqual(errors, [])
    self.assertFalse(summary["overall_pass"])
    blocked_metric = next(
      metric for metric in summary["metrics"] if metric["field"] == "blocked_by_hidden_key_point"
    )
    self.assertFalse(blocked_metric["pass"])

  def test_template_null_values_are_invalid_as_real_results(self) -> None:
    batch = json.loads(TEMPLATE_PATH.read_text(encoding="utf-8"))
    _summary, errors = evaluate_batch(batch)
    self.assertTrue(any("must be true or false" in error for error in errors))
    self.assertTrue(any("must be between 0 and 1" in error for error in errors))


if __name__ == "__main__":
  unittest.main()
