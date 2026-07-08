from __future__ import annotations

import contextlib
import os
import re
import shutil
import socket
import sys
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Iterator


ROOT = Path(__file__).resolve().parents[1]
SAVE_KEY = "game_writer_missing_phone_runtime_v1"


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:  # noqa: A002 - inherited name
        return


@contextlib.contextmanager
def static_server(root: Path) -> Iterator[str]:
    class ProjectHandler(QuietHandler):
        def __init__(self, *args: object, **kwargs: object) -> None:
            super().__init__(*args, directory=str(root), **kwargs)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]

    server = ThreadingHTTPServer(("127.0.0.1", port), ProjectHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{port}/"
    finally:
        server.shutdown()
        thread.join(timeout=5)


def chrome_executable() -> str | None:
    env_path = os.environ.get("BROWSER_EXECUTABLE")
    if env_path:
        return env_path
    for candidate in ("google-chrome", "chromium", "chromium-browser"):
        path = shutil.which(candidate)
        if path:
            return path
    return None


def assert_condition(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def run_browser_smoke() -> dict[str, object]:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:  # pragma: no cover - depends on local environment
        raise RuntimeError("Python package 'playwright' is required for browser smoke") from exc

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

            assert_condition(page.locator(".guidance-panel").count() == 0, "Guidance should not appear before observe")
            assert_no_horizontal_overflow(page)

            page.get_by_role("button", name="未发送短信").click()
            assert_single_active_observe_chain(page, "obs_unsent_sms")
            first_guidance = page.locator(".guidance-panel").inner_text()
            assert_condition("锁屏记录展开" in first_guidance, "First observe guidance missing")

            page.get_by_role("button", name="远程清除").click()
            assert_single_active_observe_chain(page, "obs_remote_wipe")
            assert_condition(
                page.locator('.background-block > .evidence-card[data-anchor-id="obs_unsent_sms"]').count() == 0,
                "Sibling observe should close the previously displayed top-level card",
            )

            page.get_by_role("button", name="未发送短信").click()
            assert_single_active_observe_chain(page, "obs_unsent_sms")
            page.locator(".evidence-card .anchor-button", has_text="02:13").first.click()
            assert_single_active_observe_chain(page, "obs_unsent_sms", "obs_0213_log")
            second_guidance = page.locator(".guidance-panel").inner_text()
            assert_condition("行动栏刷新" in second_guidance, "Choice unlock guidance missing")
            highlighted = page.locator(".choice-button.newly-unlocked").all_inner_texts()
            assert_condition(any("前往废弃地铁站" in item for item in highlighted), "Unlocked choice was not highlighted")

            page.get_by_role("button", name=re.compile("前往废弃地铁站")).click()
            page.get_by_role("button", name="临时令牌").click()
            page.get_by_role("button", name=re.compile("冻结清除队列")).click()
            page.get_by_role("button", name="出租车订单").click()
            page.get_by_role("button", name=re.compile("沿订单路线去旧员工入口")).click()

            page.wait_for_selector(".review-screen")
            review_text = page.locator(".review-screen").inner_text()
            flow_nodes = page.locator(".chapter-flow-node").count()
            locked_branches = page.locator(".flow-branches li.locked").count()
            assert_condition("本章路径图" in review_text, "Chapter review flow missing")
            assert_condition("未解锁：" in review_text, "Locked branch reason missing")
            assert_condition(flow_nodes == 3, "First chapter flow should contain 3 nodes")
            assert_condition(locked_branches > 0, "Flow should contain at least one locked branch")
            assert_review_flow_choices_not_clipped(page)
            assert_review_continue_button_visible(page)

            page.reload(wait_until="networkidle")
            restored_text = page.locator(".review-screen").inner_text()
            assert_condition("本章路径图" in restored_text, "Review state did not restore after reload")
            assert_review_continue_button_visible(page)
            assert_no_horizontal_overflow(page)

            page.evaluate(
                f"""
                () => {{
                  const payload = JSON.parse(window.localStorage.getItem('{SAVE_KEY}'));
                  payload.version = 1;
                  window.localStorage.setItem('{SAVE_KEY}', JSON.stringify(payload));
                }}
                """
            )
            page.reload(wait_until="networkidle")
            migrated_review_text = page.locator(".review-screen").inner_text()
            assert_condition("本章路径图" in migrated_review_text, "Legacy v1 save did not migrate to review state")
            assert_no_horizontal_overflow(page)

            page.evaluate(f"window.localStorage.setItem('{SAVE_KEY}', 'not-json')")
            page.reload(wait_until="networkidle")
            corrupt_notice = assert_start_scene_restored(
                page,
                "Corrupt JSON save did not fall back to first scene",
                "旧进度内容损坏",
            )

            page.evaluate(f"window.localStorage.setItem('{SAVE_KEY}', JSON.stringify({{'version': 999}}))")
            page.reload(wait_until="networkidle")
            invalid_notice = assert_start_scene_restored(
                page,
                "Invalid version save did not fall back to first scene",
                "旧进度与当前案件不兼容",
            )

            result = {
                "base_url": base_url,
                "first_guidance": first_guidance,
                "second_guidance": second_guidance,
                "highlighted_choices": highlighted,
                "flow_nodes": flow_nodes,
                "locked_branches": locked_branches,
                "legacy_save_migrated": True,
                "corrupt_save_recovered": True,
                "invalid_save_recovered": True,
                "corrupt_save_notice": corrupt_notice,
                "invalid_save_notice": invalid_notice,
            }
            browser.close()
            return result


def assert_no_horizontal_overflow(page: object) -> None:
    overflow = page.evaluate(
        """
        () => ({
          scrollWidth: document.documentElement.scrollWidth,
          clientWidth: document.documentElement.clientWidth,
          bodyScrollWidth: document.body.scrollWidth,
          innerWidth: window.innerWidth
        })
        """
    )
    max_width = max(overflow["clientWidth"], overflow["innerWidth"]) + 1
    assert_condition(
        overflow["scrollWidth"] <= max_width and overflow["bodyScrollWidth"] <= max_width,
        f"Mobile viewport has horizontal overflow: {overflow}",
    )


def assert_single_active_observe_chain(page: object, *anchor_ids: str) -> None:
    top_level_cards = page.locator(".background-block > .evidence-card")
    assert_condition(top_level_cards.count() == 1, "Only one top-level observe card should be visible")
    for anchor_id in anchor_ids:
        assert_condition(
            page.locator(f'.evidence-card[data-anchor-id="{anchor_id}"]').count() == 1,
            f"Expected active observe card missing: {anchor_id}",
        )
    visible_card_ids = page.locator(".evidence-card").evaluate_all(
        "(cards) => cards.map((card) => card.dataset.anchorId)"
    )
    assert_condition(
        visible_card_ids == list(anchor_ids),
        f"Visible observe cards should match the active chain: {visible_card_ids}",
    )


def assert_review_continue_button_visible(page: object) -> None:
    metrics = page.locator('[data-action="continue-review"]').evaluate(
        """
        (button) => {
          const rect = button.getBoundingClientRect();
          const story = document.querySelector("#storyArea");
          return {
            top: rect.top,
            bottom: rect.bottom,
            viewportHeight: window.innerHeight,
            storyScrollHeight: story.scrollHeight,
            storyClientHeight: story.clientHeight
          };
        }
        """
    )
    assert_condition(
        metrics["top"] >= 0 and metrics["bottom"] <= metrics["viewportHeight"],
        f"Continue choice should be fully visible in chapter review: {metrics}",
    )
    assert_condition(
        metrics["storyScrollHeight"] >= metrics["storyClientHeight"],
        f"Chapter review should scroll inside the story area instead of clipping choices: {metrics}",
    )


def assert_review_flow_choices_not_clipped(page: object) -> None:
    metrics = page.locator(".flow-branches li").evaluate_all(
        """
        (items) => items.map((item) => {
          const rect = item.getBoundingClientRect();
          const storyRect = document.querySelector("#storyArea").getBoundingClientRect();
          return {
            text: item.textContent.trim(),
            top: rect.top,
            bottom: rect.bottom,
            storyBottom: storyRect.bottom,
            clipped: item.scrollHeight > item.clientHeight + 1 || item.scrollWidth > item.clientWidth + 1
          };
        })
        """
    )
    clipped = [item for item in metrics if item["clipped"]]
    below_story = [item for item in metrics if item["bottom"] > item["storyBottom"] + 1]
    assert_condition(not clipped, f"Review flow choices should not clip their text: {clipped}")
    assert_condition(not below_story, f"Review flow choices should not be hidden behind the action bar: {below_story}")


def assert_start_scene_restored(page: object, message: str, expected_notice: str) -> str:
    page.wait_for_selector('[data-anchor-id="obs_unsent_sms"]')
    assert_condition(page.locator("#sceneTitle").inner_text() == "锁屏上的半句话", message)
    assert_condition(page.locator(".review-screen").count() == 0, message)
    assert_condition(page.locator(".ending-screen").count() == 0, message)
    notice = page.locator('[data-notice="save-recovery"]')
    assert_condition(notice.count() == 1, f"{message}: recovery notice missing")
    notice_text = notice.inner_text()
    assert_condition(expected_notice in notice_text, f"{message}: recovery notice copy missing")
    assert_no_horizontal_overflow(page)
    return notice_text


def main() -> int:
    try:
        result = run_browser_smoke()
    except Exception as exc:  # noqa: BLE001 - command should print actionable failure
        print(f"Browser smoke failed: {exc}", file=sys.stderr)
        return 1
    print("Browser smoke passed")
    print(f"- flow_nodes: {result['flow_nodes']}")
    print(f"- locked_branches: {result['locked_branches']}")
    print(f"- legacy_save_migrated: {result['legacy_save_migrated']}")
    print(f"- corrupt_save_recovered: {result['corrupt_save_recovered']}")
    print(f"- invalid_save_recovered: {result['invalid_save_recovered']}")
    print(f"- corrupt_save_notice: {result['corrupt_save_notice']}")
    print(f"- invalid_save_notice: {result['invalid_save_notice']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
