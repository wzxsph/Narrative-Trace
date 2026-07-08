from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from gamegen.llm_scene_review import normalize_llm_scene_review


class LLMSceneReviewTest(unittest.TestCase):
  def test_normalize_accepts_valid_review(self) -> None:
    review = normalize_llm_scene_review(
      {
        "scene_id": "ch01_phone_lock",
        "verdict": "pass",
        "risk_flags": ["none"],
        "notes": ["结构和蓝图一致。"],
      },
      "ch01_phone_lock",
    )

    self.assertEqual(review["schema_version"], "llm_scene_review_v0_1")
    self.assertEqual(review["scene_id"], "ch01_phone_lock")

  def test_normalize_rejects_wrong_scene_id(self) -> None:
    with self.assertRaisesRegex(RuntimeError, "wrong scene_id"):
      normalize_llm_scene_review(
        {
          "scene_id": "other_scene",
          "verdict": "pass",
          "risk_flags": ["none"],
          "notes": ["ok"],
        },
        "ch01_phone_lock",
      )

  def test_normalize_rejects_unknown_risk_flag(self) -> None:
    with self.assertRaisesRegex(RuntimeError, "invalid risk flag"):
      normalize_llm_scene_review(
        {
          "scene_id": "ch01_phone_lock",
          "verdict": "pass",
          "risk_flags": ["made_up"],
          "notes": ["ok"],
        },
        "ch01_phone_lock",
      )


if __name__ == "__main__":
  unittest.main()
