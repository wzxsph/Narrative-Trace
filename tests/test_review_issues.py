from __future__ import annotations

import unittest

from gamegen.review_issues import (
  build_review_issues,
  evaluate_review_issue_release_policy,
  validate_review_issue_release_policy,
  validate_review_issues,
)


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

  def test_release_policy_warns_on_open_major_nonblocking_issue(self) -> None:
    review_issues = build_review_issues(
      "missing_phone",
      {
        "schema_version": "llm_scene_review_v0_1",
        "scene_id": "ch01_phone_lock",
        "verdict": "revise",
        "risk_flags": ["missing_observe_payoff"],
        "notes": ["观察缺少收益。"],
      },
    )

    policy = evaluate_review_issue_release_policy(review_issues)

    self.assertEqual(validate_review_issue_release_policy(policy), [])
    self.assertEqual(policy["status"], "passed")
    self.assertEqual(policy["summary"]["open_major"], 1)
    self.assertEqual(policy["summary"]["active_nonblocking"], 1)
    self.assertEqual(len(policy["warning_issue_ids"]), 1)

  def test_release_policy_blocks_explicit_blocking_issue(self) -> None:
    review_issues = build_review_issues(
      "missing_phone",
      {
        "schema_version": "llm_scene_review_v0_1",
        "scene_id": "ch01_phone_lock",
        "verdict": "revise",
        "risk_flags": ["missing_observe_payoff"],
        "notes": ["观察缺少收益。"],
      },
    )
    review_issues["issues"][0]["blocking"] = True

    policy = evaluate_review_issue_release_policy(review_issues)

    self.assertEqual(validate_review_issue_release_policy(policy), [])
    self.assertEqual(policy["status"], "blocked")
    self.assertEqual(policy["blocking_issue_ids"], [review_issues["issues"][0]["id"]])
    self.assertEqual(policy["summary"]["active_blocking"], 1)

  def test_release_policy_passes_with_open_minor_warning(self) -> None:
    review_issues = build_review_issues(
      "missing_phone",
      {
        "schema_version": "llm_scene_review_v0_1",
        "scene_id": "ch01_phone_lock",
        "verdict": "revise",
        "risk_flags": ["state_echo_missing"],
        "notes": ["状态缺少回声。"],
      },
    )

    policy = evaluate_review_issue_release_policy(review_issues)

    self.assertEqual(validate_review_issue_release_policy(policy), [])
    self.assertEqual(policy["status"], "passed")
    self.assertEqual(policy["summary"]["open_minor"], 1)
    self.assertEqual(len(policy["warning_issue_ids"]), 1)


if __name__ == "__main__":
  unittest.main()
