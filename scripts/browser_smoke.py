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
            first_guidance = page.locator(".guidance-panel").inner_text()
            assert_condition("锁屏记录展开" in first_guidance, "First observe guidance missing")

            page.locator(".evidence-card .anchor-button", has_text="02:13").first.click()
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

            page.reload(wait_until="networkidle")
            restored_text = page.locator(".review-screen").inner_text()
            assert_condition("本章路径图" in restored_text, "Review state did not restore after reload")
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
    print(f"- corrupt_save_recovered: {result['corrupt_save_recovered']}")
    print(f"- invalid_save_recovered: {result['invalid_save_recovered']}")
    print(f"- corrupt_save_notice: {result['corrupt_save_notice']}")
    print(f"- invalid_save_notice: {result['invalid_save_notice']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
