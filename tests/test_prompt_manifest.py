from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from gamegen.demo_agent import export_game
from gamegen.prompt_manifest import active_prompt_set_id, load_prompt_manifest


GAME_PATH = ROOT / "generated" / "missing_phone_v0" / "game.json"
MANIFEST_PATH = ROOT / "prompts" / "manifest.json"


def load_game() -> dict:
  return json.loads(GAME_PATH.read_text(encoding="utf-8"))


class PromptManifestTest(unittest.TestCase):
  def test_active_prompt_set_is_declared(self) -> None:
    manifest = load_prompt_manifest(MANIFEST_PATH)
    active_id = active_prompt_set_id(MANIFEST_PATH)
    declared_ids = {item["id"] for item in manifest["prompt_sets"]}
    self.assertIn(active_id, declared_ids)

  def test_export_trace_records_active_prompt_set(self) -> None:
    with tempfile.TemporaryDirectory() as tmp:
      export_game(load_game(), tmp)
      trace = json.loads((Path(tmp) / "generation_trace.jsonl").read_text(encoding="utf-8"))
      self.assertEqual(trace["prompt_set"], active_prompt_set_id(MANIFEST_PATH))

  def test_manifest_rejects_undeclared_active_prompt_set(self) -> None:
    with tempfile.TemporaryDirectory() as tmp:
      manifest_path = Path(tmp) / "manifest.json"
      manifest_path.write_text(
        json.dumps(
          {
            "schema_version": "game_writer_prompt_manifest_v0_1",
            "active_prompt_set": "missing",
            "prompt_sets": [],
          },
          ensure_ascii=False,
        ),
        encoding="utf-8",
      )
      with self.assertRaises(ValueError):
        active_prompt_set_id(manifest_path)


if __name__ == "__main__":
  unittest.main()
