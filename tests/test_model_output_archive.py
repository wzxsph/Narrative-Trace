from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from gamegen.model_output_archive import (
  archive_model_output_sample,
  assert_no_unredacted_secrets,
  redact_sample_text,
  validate_model_output_archive,
)
from gamegen.prompt_manifest import active_prompt_set_id


class ModelOutputArchiveTest(unittest.TestCase):
  def test_redacts_common_secret_shapes(self) -> None:
    raw = (
      'OPENAI_API_KEY=sk-testsecret123456789\n'
      '{"api_key":"secret-value","authorization":"Bearer abcdefghijklmnop"}\n'
      "contact reviewer@example.com"
    )

    redacted = redact_sample_text(raw)

    self.assertIn("OPENAI_API_KEY=REDACTED", redacted)
    self.assertIn('"api_key":"REDACTED"', redacted)
    self.assertIn('"authorization":"REDACTED"', redacted)
    self.assertIn("[REDACTED_EMAIL]", redacted)
    self.assertNotIn("sk-testsecret", redacted)
    self.assertNotIn("reviewer@example.com", redacted)
    assert_no_unredacted_secrets(redacted)

  def test_archives_sample_with_manifest_metadata(self) -> None:
    with tempfile.TemporaryDirectory() as tmp:
      tmp_path = Path(tmp)
      raw_path = tmp_path / "raw_sample.txt"
      raw_path.write_text(
        "model returned invalid JSON\nLLM_API_KEY=sk-live1234567890\nuser=a@example.com\n",
        encoding="utf-8",
      )
      out_dir = tmp_path / "archive"

      entry = archive_model_output_sample(
        raw_path,
        out_dir=out_dir,
        sample_id="first_scene_polish_fail_001",
        provider="openai_compatible",
        model="sample-model",
        prompt_set=active_prompt_set_id(),
        source="first_scene_llm_polish_v0_1",
        notes="invalid json sample",
        created_at="2026-07-08T00:00:00.000Z",
      )

      sample_text = (out_dir / entry["file"]).read_text(encoding="utf-8")
      manifest = json.loads((out_dir / "sample_manifest.json").read_text(encoding="utf-8"))

      self.assertEqual(entry["provider"], "openai_compatible")
      self.assertEqual(entry["model"], "sample-model")
      self.assertEqual(entry["prompt_set"], active_prompt_set_id())
      self.assertIn("LLM_API_KEY=REDACTED", sample_text)
      self.assertIn("[REDACTED_EMAIL]", sample_text)
      self.assertNotIn("sk-live", sample_text)
      self.assertEqual(manifest["samples"][0]["id"], "first_scene_polish_fail_001")
      self.assertEqual(manifest["samples"][0]["sha256"], entry["sha256"])
      self.assertEqual(validate_model_output_archive(out_dir), [])

  def test_rejects_bad_sample_id_and_undeclared_prompt_set(self) -> None:
    with tempfile.TemporaryDirectory() as tmp:
      raw_path = Path(tmp) / "raw_sample.txt"
      raw_path.write_text("{}", encoding="utf-8")

      with self.assertRaises(ValueError):
        archive_model_output_sample(
          raw_path,
          out_dir=Path(tmp) / "archive",
          sample_id="../escape",
          provider="openai_compatible",
          model="sample-model",
          prompt_set=active_prompt_set_id(),
          source="first_scene_llm_polish_v0_1",
        )

      with self.assertRaises(ValueError):
        archive_model_output_sample(
          raw_path,
          out_dir=Path(tmp) / "archive",
          sample_id="valid_sample_001",
          provider="openai_compatible",
          model="sample-model",
          prompt_set="missing_prompt_set",
          source="first_scene_llm_polish_v0_1",
        )

  def test_archive_validator_catches_tampered_sample(self) -> None:
    with tempfile.TemporaryDirectory() as tmp:
      tmp_path = Path(tmp)
      raw_path = tmp_path / "raw_sample.txt"
      raw_path.write_text("safe sample", encoding="utf-8")
      out_dir = tmp_path / "archive"
      entry = archive_model_output_sample(
        raw_path,
        out_dir=out_dir,
        sample_id="tamper_sample_001",
        provider="openai_compatible",
        model="sample-model",
        prompt_set=active_prompt_set_id(),
        source="first_scene_llm_polish_v0_1",
      )

      sample_path = out_dir / entry["file"]
      sample_path.write_text("tampered Bearer abcdefghijklmnop user@example.com\n", encoding="utf-8")

      errors = validate_model_output_archive(out_dir)

      self.assertTrue(any("unredacted secret" in error for error in errors))
      self.assertTrue(any("sha256 mismatch" in error for error in errors))

  def test_archive_validator_accepts_empty_manifest(self) -> None:
    with tempfile.TemporaryDirectory() as tmp:
      out_dir = Path(tmp) / "archive"
      out_dir.mkdir()
      (out_dir / "sample_manifest.json").write_text(
        json.dumps(
          {
            "schema_version": "game_writer_model_output_samples_v0_1",
            "description": "empty",
            "samples": [],
          },
          ensure_ascii=False,
        ),
        encoding="utf-8",
      )

      self.assertEqual(validate_model_output_archive(out_dir), [])


if __name__ == "__main__":
  unittest.main()
