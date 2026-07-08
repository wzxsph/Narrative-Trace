from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.content_qa_report import run_content_qa


GAME_PATH = ROOT / "generated" / "missing_phone_v0" / "game.json"


def load_game() -> dict:
  return json.loads(GAME_PATH.read_text(encoding="utf-8"))


def flatten_anchors(anchors: list[dict]) -> list[dict]:
  output = []
  for anchor in anchors:
    output.append(anchor)
    output.extend(flatten_anchors(anchor.get("opens_fragment", {}).get("nested_anchors", [])))
  return output


class ContentQATest(unittest.TestCase):
  def test_current_demo_has_no_content_qa_messages(self) -> None:
    messages = run_content_qa(load_game())
    self.assertEqual(messages, [])

  def test_hidden_optional_observe_cannot_unlock_global_choice(self) -> None:
    game = copy.deepcopy(load_game())
    first_scene = game["scenes"][0]
    anchors = {
      anchor["id"]: anchor
      for block in first_scene["background_blocks"]
      for anchor in flatten_anchors(block["observe_anchors"])
    }
    anchors["obs_0213_log"]["discoverability"] = "hidden_optional"

    messages = run_content_qa(game)
    self.assertTrue(
      any("hidden_optional observe must not unlock" in message.message for message in messages)
    )

  def test_main_scene_must_have_obvious_observe_entry(self) -> None:
    game = copy.deepcopy(load_game())
    first_scene = game["scenes"][0]
    for block in first_scene["background_blocks"]:
      for anchor in flatten_anchors(block["observe_anchors"]):
        anchor["discoverability"] = "subtle"

    messages = run_content_qa(game)
    self.assertTrue(any("at least one obvious observe" in message.message for message in messages))

  def test_choice_requires_description_and_outcome(self) -> None:
    game = copy.deepcopy(load_game())
    game["scenes"][0]["choices"][0]["description"] = ""
    game["scenes"][0]["choices"][0]["outcome"] = ""

    messages = run_content_qa(game)
    self.assertTrue(any("Choice must have a description" in message.message for message in messages))
    self.assertTrue(any("Choice must have an outcome" in message.message for message in messages))


if __name__ == "__main__":
  unittest.main()
