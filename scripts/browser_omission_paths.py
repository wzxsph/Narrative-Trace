#!/usr/bin/env python3
from __future__ import annotations

import sys

from browser_smoke import ROOT, assert_condition, assert_no_horizontal_overflow, chrome_executable, static_server


def run_browser_omission_paths() -> dict[str, object]:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:  # pragma: no cover - depends on local environment
        raise RuntimeError("Python package 'playwright' is required for browser omission paths") from exc

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
            page.wait_for_selector('button[data-anchor-id="obs_unsent_sms"]')

            assert_choice_hidden(page, "choice_delay_wipe")
            assert_choice_hidden(page, "choice_go_station")
            assert_choice_hidden(page, "choice_confront_chen")

            click_observe(page, "obs_remote_wipe")
            assert_choice_hidden(page, "choice_delay_wipe")
            assert_no_horizontal_overflow(page)

            click_choice(page, "choice_call_chen")
            click_choice(page, "choice_leave_unfrozen")
            click_choice(page, "choice_follow_old_address")

            page.wait_for_selector(".review-screen")
            delay_branch = locked_branch_text(page, "choice_delay_wipe")
            station_branch = locked_branch_text(page, "choice_go_station")
            assert_condition("远程清除暂停窗口" in delay_branch, "Delay wipe locked reason should name missing pause window")
            assert_condition("废弃地铁站定位" in station_branch, "Station path locked reason should name missing location clue")
            assert_condition(
                page.locator('.flow-branches li.unlocked[data-choice-id="choice_delay_wipe"]').count() == 0,
                "Delay wipe should not be marked unlocked when its requirement is unmet",
            )
            assert_condition(
                page.locator('.flow-branches li.pending[data-choice-id="choice_delay_wipe"]').count() == 0,
                "Delay wipe should not be pending after a non-unlocking observe",
            )
            assert_no_horizontal_overflow(page)

            browser.close()
            return {
                "hidden_choices_blocked": True,
                "locked_reason_delay": delay_branch,
                "locked_reason_station": station_branch,
            }


def click_observe(page: object, anchor_id: str) -> None:
    locator = page.locator(f'button[data-anchor-id="{anchor_id}"]')
    assert_condition(locator.count() > 0, f"Observe anchor not found: {anchor_id}")
    locator.first.click()


def click_choice(page: object, choice_id: str) -> None:
    locator = page.locator(f'button[data-choice-id="{choice_id}"]')
    assert_condition(locator.count() > 0, f"Choice not visible or not found: {choice_id}")
    locator.first.click()


def assert_choice_hidden(page: object, choice_id: str) -> None:
    assert_condition(
        page.locator(f'button[data-choice-id="{choice_id}"]').count() == 0,
        f"Choice should be hidden until requirements are met: {choice_id}",
    )


def locked_branch_text(page: object, choice_id: str) -> str:
    locator = page.locator(f'.flow-branches li.locked[data-choice-id="{choice_id}"]')
    assert_condition(locator.count() == 1, f"Locked branch missing from review: {choice_id}")
    text = locator.inner_text()
    assert_condition("未解锁" in text, f"Locked branch should be explicit: {choice_id}")
    return text


def main() -> int:
    try:
        result = run_browser_omission_paths()
    except Exception as exc:  # noqa: BLE001 - command should print actionable failure
        print(f"Browser omission paths failed: {exc}", file=sys.stderr)
        return 1

    print("Browser omission paths passed")
    print(f"- hidden_choices_blocked: {result['hidden_choices_blocked']}")
    print(f"- locked_reason_delay: {result['locked_reason_delay']}")
    print(f"- locked_reason_station: {result['locked_reason_station']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
