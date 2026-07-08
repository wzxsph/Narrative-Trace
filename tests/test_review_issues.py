from __future__ import annotations

import unittest

from gamegen.review_issues import build_review_issues, validate_review_issues


class ReviewIssuesTest(unittest.TestCase):
  def test_revise_review_builds_open_issues(self) -> None:
    review_issues = build_review_issues(
      "missing_phone",
      {
        "schema_version": "llm_scene_review_v0_1",
        "scene_id": "ch01_phone_lock",
        "verdict": "revise",
        "risk_flags": ["missing_observe_payoff", "state_echo_missing"],
        "notes": ["观察没有收益。", "状态缺少回声。"],
      },
    )

    self.assertEqual(validate_review_issues(review_issues), [])
    self.assertEqual(len(review_issues["issues"]), 2)
    self.assertEqual(review_issues["issues"][0]["status"], "open")
    self.assertFalse(review_issues["issues"][0]["blocking"])

  def test_pass_review_builds_empty_issue_list(self) -> None:
    review_issues = build_review_issues(
      "missing_phone",
      {
        "schema_version": "llm_scene_review_v0_1",
        "scene_id": "ch01_phone_lock",
        "verdict": "pass",
        "risk_flags": ["none"],
        "notes": ["可以通过。"],
      },
    )

    self.assertEqual(validate_review_issues(review_issues), [])
    self.assertEqual(review_issues["issues"], [])

  def test_invalid_issue_status_fails(self) -> None:
    review_issues = build_review_issues(
      "missing_phone",
      {
        "schema_version": "llm_scene_review_v0_1",
        "scene_id": "ch01_phone_lock",
        "verdict": "revise",
        "risk_flags": ["tone_drift"],
        "notes": ["语气漂移。"],
      },
    )
    review_issues["issues"][0]["status"] = "later"

    messages = validate_review_issues(review_issues)

    self.assertTrue(any(message.level == "error" and message.location == "issues[0].status" for message in messages))


if __name__ == "__main__":
  unittest.main()
