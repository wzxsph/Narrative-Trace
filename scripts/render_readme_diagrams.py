from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "doc" / "readme_diagrams" / "readme_diagrams.html"
OUTPUT_DIR = ROOT / "screenshots" / "readme-diagrams"
DIAGRAM_IDS = [
    "game-loop",
    "interaction-map",
    "runtime-architecture",
    "ai-pipeline",
    "release-gates",
    "state-ending-map",
    "product-boundary",
]


def chrome_executable() -> str | None:
    env_path = os.environ.get("BROWSER_EXECUTABLE")
    if env_path:
        return env_path
    for candidate in ("google-chrome", "chromium", "chromium-browser"):
        path = shutil.which(candidate)
        if path:
            return path
    return None


def main() -> int:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError("Python package 'playwright' is required to render README diagrams") from exc

    executable = chrome_executable()
    if not executable:
        raise RuntimeError("Chrome/Chromium executable not found. Set BROWSER_EXECUTABLE.")

    if not SOURCE.exists():
        raise FileNotFoundError(SOURCE)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=executable,
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        page = browser.new_page(viewport={"width": 1280, "height": 900}, device_scale_factor=2)
        page.goto(SOURCE.as_uri(), wait_until="networkidle")
        for diagram_id in DIAGRAM_IDS:
            locator = page.locator(f"#{diagram_id}")
            locator.wait_for(state="visible", timeout=5000)
            output_path = OUTPUT_DIR / f"{diagram_id}.png"
            locator.screenshot(path=str(output_path))
            print(output_path.relative_to(ROOT))
        browser.close()

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001 - CLI should print actionable failure
        print(f"Render README diagrams failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
