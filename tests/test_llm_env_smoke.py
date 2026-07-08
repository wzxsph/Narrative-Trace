from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class LLMEnvSmokeScriptTest(unittest.TestCase):
  def test_missing_env_fails_without_secret_output(self) -> None:
    env = os.environ.copy()
    env["LLM_BASE_URL"] = ""
    env["LLM_API_KEY"] = ""
    proc = subprocess.run(
      [sys.executable, str(ROOT / "scripts" / "llm_env_smoke_test.py")],
      cwd=ROOT,
      env=env,
      text=True,
      capture_output=True,
      check=False,
    )

    self.assertNotEqual(proc.returncode, 0)
    self.assertIn("missing LLM_BASE_URL or LLM_API_KEY", proc.stderr)
    self.assertNotIn("sk-", proc.stdout + proc.stderr)
    self.assertNotIn("Bearer", proc.stdout + proc.stderr)


if __name__ == "__main__":
  unittest.main()
