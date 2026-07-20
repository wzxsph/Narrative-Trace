#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from gamegen.save_contract import DEFAULT_SAVE_CONTRACT, load_save_contract
from scripts.browser_smoke import (
    LEGACY_SAVE_KEY,
    SAVE_KEY,
    ROOT,
    assert_condition,
    assert_no_horizontal_overflow,
    chrome_executable,
    static_server,
)


def run_browser_save_contract() -> list[dict[str, object]]:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:  # pragma: no cover - depends on local environment
        raise RuntimeError("Python package 'playwright' is required for browser save contract") from exc

    executable = chrome_executable()
    if not executable:
        raise RuntimeError("Chrome/Chromium executable not found. Set BROWSER_EXECUTABLE.")

    contract = load_save_contract(DEFAULT_SAVE_CONTRACT)
    with static_server(ROOT) as base_url:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                executable_path=executable,
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage"],
            )
            page = browser.new_page(viewport={"width": 390, "height": 844}, is_mobile=True)
            results = [run_case(page, base_url, case, contract["current_save_version"]) for case in contract["cases"]]
            browser.close()
            return results


def run_case(page: object, base_url: str, case: dict[str, Any], current_version: int) -> dict[str, object]:
    page.goto(base_url, wait_until="networkidle")
    page.evaluate("window.localStorage.clear()")
    write_save_case(page, case)
    page.reload(wait_until="networkidle")
    expect = case["expect"]

    if expect.get("restores"):
        screen = expect.get("screen")
        if screen == "review":
            page.wait_for_selector(".review-screen")
            body = page.locator(".review-screen").inner_text()
            assert_condition("本章路径图" in body, f"{case['id']}: review did not restore")
        elif screen == "ending":
            page.wait_for_selector(".ending-screen")
            body = page.locator(".ending-screen").inner_text()
            assert_condition("结局标签" in body, f"{case['id']}: ending profile did not restore")
        else:
            raise AssertionError(f"{case['id']}: unsupported expected screen {screen!r}")
        assert_condition(page.locator('[data-notice="save-recovery"]').count() == 0, f"{case['id']}: unexpected recovery notice")
        saved_schema = page.evaluate(f"JSON.parse(window.localStorage.getItem('{SAVE_KEY}')).schema_version")
        assert_condition(saved_schema == "narrative_save_v1", f"{case['id']}: namespaced V1 save was not persisted")
        assert_condition(
            page.evaluate("(key) => window.localStorage.getItem(key)", LEGACY_SAVE_KEY) is None,
            f"{case['id']}: legacy key remained after successful migration",
        )
        assert_no_horizontal_overflow(page)
        return {"id": case["id"], "screen": screen, "restored": True}

    page.wait_for_selector('[data-anchor-id="obs_unsent_sms"]')
    assert_condition(page.locator("#sceneTitle").inner_text() == "锁屏上的半句话", f"{case['id']}: fallback did not reach start")
    notice = page.locator('[data-notice="save-recovery"]')
    assert_condition(notice.count() == 1, f"{case['id']}: fallback notice missing")
    notice_text = notice.inner_text()
    expected_notice = expect.get("recovery_notice_contains", "")
    assert_condition(expected_notice in notice_text, f"{case['id']}: fallback notice copy missing")
    assert_no_horizontal_overflow(page)
    return {"id": case["id"], "screen": "fallback", "restored": False}


def write_save_case(page: object, case: dict[str, Any]) -> None:
    if "raw_save" in case:
        raw_save = case["raw_save"]
        page.evaluate("(args) => window.localStorage.setItem(args.key, args.value)", {"key": LEGACY_SAVE_KEY, "value": raw_save})
        return
    page.evaluate(
        "(args) => window.localStorage.setItem(args.key, JSON.stringify(args.payload))",
        {"key": LEGACY_SAVE_KEY, "payload": case["payload"]},
    )


def main() -> int:
    try:
        results = run_browser_save_contract()
    except Exception as exc:  # noqa: BLE001 - CLI should print actionable failure
        print(f"Browser save contract failed: {exc}", file=sys.stderr)
        return 1

    print("Browser save contract passed")
    for result in results:
        print(f"- {result['id']}: {result['screen']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
