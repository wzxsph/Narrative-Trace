#!/usr/bin/env python3
from __future__ import annotations

import sys

from browser_smoke import ROOT, assert_condition, assert_no_horizontal_overflow, chrome_executable, static_server


def run_browser_a11y_smoke() -> dict[str, object]:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:  # pragma: no cover - depends on local environment
        raise RuntimeError("Python package 'playwright' is required for browser accessibility smoke") from exc

    executable = chrome_executable()
    if not executable:
        raise RuntimeError("Chrome/Chromium executable not found. Set BROWSER_EXECUTABLE.")

    with static_server(ROOT) as base_url:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                executable_path=executable,
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage"],
            )
            page = browser.new_page(viewport={"width": 390, "height": 844}, is_mobile=True)
            page.goto(base_url, wait_until="networkidle")
            page.evaluate("window.localStorage.clear()")
            page.reload(wait_until="networkidle")

            map_button = page.locator("#mapButton")
            assert_condition(map_button.get_attribute("aria-controls") == "pathPanel", "Map button missing aria-controls")
            assert_condition(map_button.get_attribute("aria-expanded") == "false", "Map button should start collapsed")
            assert_condition(page.locator("#pathPanel").get_attribute("aria-hidden") == "true", "Closed path panel should be hidden")

            page.keyboard.press("Tab")
            assert_condition(page.evaluate("document.activeElement.id") == "mapButton", "Tab should focus map button first")
            page.keyboard.press("Enter")
            assert_condition(map_button.get_attribute("aria-expanded") == "true", "Map button should expand via keyboard")
            assert_condition(page.locator("#pathPanel").get_attribute("aria-hidden") == "false", "Open path panel should be visible")
            assert_condition(page.evaluate("document.activeElement.id") == "closeMapButton", "Opening path panel should focus close")

            page.keyboard.press("Escape")
            assert_condition(map_button.get_attribute("aria-expanded") == "false", "Escape should collapse path panel")
            assert_condition(page.locator("#pathPanel").get_attribute("aria-hidden") == "true", "Closed path panel should be hidden after Escape")
            assert_condition(page.evaluate("document.activeElement.id") == "mapButton", "Closing path panel should return focus")

            focus_anchor(page, "obs_unsent_sms")
            page.keyboard.press("Enter")
            guidance = page.locator(".guidance-panel").inner_text()
            assert_condition("锁屏记录展开" in guidance, "Keyboard activation should open first observe")
            assert_no_horizontal_overflow(page)

            browser.close()
            return {
                "map_keyboard_toggle": True,
                "escape_closes_map": True,
                "observe_keyboard_activation": True,
            }


def focus_anchor(page: object, anchor_id: str) -> None:
    for _ in range(20):
        page.keyboard.press("Tab")
        active_anchor_id = page.evaluate("document.activeElement?.dataset?.anchorId || ''")
        if active_anchor_id == anchor_id:
            return
    raise AssertionError(f"Could not focus anchor via Tab: {anchor_id}")


def main() -> int:
    try:
        result = run_browser_a11y_smoke()
    except Exception as exc:  # noqa: BLE001 - command should print actionable failure
        print(f"Browser accessibility smoke failed: {exc}", file=sys.stderr)
        return 1

    print("Browser accessibility smoke passed")
    print(f"- map_keyboard_toggle: {result['map_keyboard_toggle']}")
    print(f"- escape_closes_map: {result['escape_closes_map']}")
    print(f"- observe_keyboard_activation: {result['observe_keyboard_activation']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
