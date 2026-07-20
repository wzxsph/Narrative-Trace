from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.build_static_bundle import build_static_bundle
from gamegen.kernel_contract import validate_kernel_document


PACK_ROOT = ROOT / "content_packs" / "missing_phone" / "v1"


class FrameworkV1RuntimeTest(unittest.TestCase):
    def test_runtime_config_selects_v1_pack_without_legacy_game_path(self) -> None:
        config = json.loads((ROOT / "runtime-config.json").read_text(encoding="utf-8"))
        self.assertEqual(config["pack"], "content_packs/missing_phone/v1")
        sources = "\n".join(
            path.read_text(encoding="utf-8")
            for path in [ROOT / "src" / "app.js", *(ROOT / "src" / "runtime").glob("*.js")]
        )
        self.assertNotIn("generated/missing_phone_v0", sources)
        self.assertNotIn('"clues.archive_ready": "归档包"', sources)

    def test_javascript_engine_and_save_contract(self) -> None:
        completed = subprocess.run(
            ["node", "tests/runtime_contract.mjs"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        evidence = json.loads(completed.stdout)
        self.assertEqual(evidence["schema"], "narrative_save_v1")
        self.assertTrue(evidence["write_failure_visible"])
        self.assertEqual(validate_kernel_document("save.schema.json", evidence["payload"]), [])

    def test_static_bundle_contains_one_selected_pack_and_runtime_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "site"
            report = build_static_bundle(PACK_ROOT, output)
            files = {path.relative_to(output).as_posix() for path in output.rglob("*") if path.is_file()}
            self.assertEqual(report["pack"], "missing_phone@1.0.0")
            self.assertIn("content_packs/missing_phone/1.0.0/pack.json", files)
            self.assertIn("src/runtime/engine.js", files)
            self.assertFalse(any(path.startswith("generated/") for path in files))
            self.assertFalse(any("loop_packages" in path for path in files))

    def test_bundle_clis_require_explicit_pack(self) -> None:
        static = subprocess.run(
            [sys.executable, "scripts/build_static_bundle.py", "--output", "/tmp/unused-framework-v1-site"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        worker = subprocess.run(
            ["node", "scripts/build_game_worker_bundle.mjs"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(static.returncode, 0)
        self.assertIn("--pack", static.stderr)
        self.assertNotEqual(worker.returncode, 0)
        self.assertIn("--pack is required", worker.stderr)


if __name__ == "__main__":
    unittest.main()
