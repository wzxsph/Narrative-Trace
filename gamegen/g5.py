from __future__ import annotations

import copy
import json
import tempfile
from pathlib import Path
from typing import Any

from .content_pack import ContentPackContext
from .gates import GateMessage, GateResult, run_g4


ROOT = Path(__file__).resolve().parents[1]
LEGACY_SAVE_KEY = "game_writer_missing_phone_runtime_v1"


def run_g5(context: ContentPackContext, digest: str) -> GateResult:
    result = GateResult("G5", digest)
    try:
        result.evidence = run_browser_pack_g5(context, digest)
    except Exception as exc:  # noqa: BLE001 - gate converts runtime failures to evidence
        result.errors.append(GateMessage("runtime.e2e", "browser", str(exc)))
    return result.finish()


def run_browser_pack_g5(context: ContentPackContext, digest: str) -> dict[str, Any]:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:  # pragma: no cover - environment dependency
        raise RuntimeError("Python package 'playwright' is required for G5") from exc
    from scripts.browser_smoke import assert_condition, assert_no_horizontal_overflow, chrome_executable, static_server
    from scripts.build_static_bundle import build_static_bundle

    executable = chrome_executable()
    if not executable:
        raise RuntimeError("Chrome/Chromium executable not found. Set BROWSER_EXECUTABLE.")
    g4 = run_g4(context, digest)
    if g4.status != "passed":
        raise RuntimeError("G4 witnesses are unavailable")
    witnesses = g4.evidence["ending_witnesses"]
    save_key = f"narrative_trace.save.{context.manifest['pack_id']}.{context.manifest['version']}"

    with tempfile.TemporaryDirectory(prefix="narrative-g5-") as temp:
        bundle_root = Path(temp) / "site"
        build_static_bundle(context.root, bundle_root)
        with static_server(bundle_root) as base_url:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(
                    executable_path=executable,
                    headless=True,
                    args=["--no-sandbox", "--disable-dev-shm-usage"],
                )
                page = browser.new_page(viewport={"width": 390, "height": 844}, is_mobile=True)
                replayed = replay_witnesses(page, base_url, witnesses, assert_condition, assert_no_horizontal_overflow)
                save_evidence = verify_save_contract(page, base_url, save_key, assert_condition)
                isolation_evidence = verify_pack_save_isolation(page, base_url, save_key, assert_condition)
                accessibility_evidence = verify_keyboard_and_viewports(
                    browser, page, base_url, assert_condition, assert_no_horizontal_overflow
                )
                fallback_evidence = verify_surface_fallbacks(
                    browser, base_url, context, assert_condition
                )
                experimental_evidence = verify_experimental_notice(
                    browser, base_url, context, assert_condition
                )
                browser.close()

    return {
        "witness_paths_replayed": replayed,
        "save_contract": save_evidence,
        "pack_save_isolation": isolation_evidence,
        "accessibility_and_viewports": accessibility_evidence,
        "surface_fallbacks": fallback_evidence,
        "experimental_notice": experimental_evidence,
    }


def replay_witnesses(page: Any, base_url: str, witnesses: dict[str, list[dict[str, str]]], assert_condition: Any, assert_no_overflow: Any) -> list[str]:
    replayed: list[str] = []
    for ending_id, steps in sorted(witnesses.items()):
        page.goto(base_url, wait_until="networkidle")
        page.evaluate("window.localStorage.clear()")
        page.reload(wait_until="networkidle")
        for step in steps:
            continue_review(page)
            attribute = "anchor-id" if step["kind"] == "anchor" else "action-id"
            locator = page.locator(f'button[data-{attribute}="{step["id"]}"]')
            assert_condition(locator.count() > 0, f"G4 witness step is not replayable: {step}")
            locator.first.click()
            if step["kind"] == "action":
                continue_review(page)
            assert_no_overflow(page)
        ending = page.locator(f'.ending-screen[data-ending-id="{ending_id}"]')
        assert_condition(ending.count() == 1, f"Witness reached the wrong ending: {ending_id}")
        page.reload(wait_until="networkidle")
        assert_condition(
            page.locator(f'.ending-screen[data-ending-id="{ending_id}"]').count() == 1,
            f"Ending did not restore: {ending_id}",
        )
        replayed.append(ending_id)
    return replayed


def verify_save_contract(page: Any, base_url: str, save_key: str, assert_condition: Any) -> dict[str, Any]:
    fixture = json.loads((ROOT / "examples" / "fixtures" / "save_contract" / "save_cases.json").read_text(encoding="utf-8"))
    legacy = fixture["cases"][0]["payload"]
    page.goto(base_url, wait_until="networkidle")
    page.evaluate("window.localStorage.clear()")
    page.evaluate(
        "(args) => window.localStorage.setItem(args.key, JSON.stringify(args.payload))",
        {"key": LEGACY_SAVE_KEY, "payload": legacy},
    )
    page.reload(wait_until="networkidle")
    assert_condition(page.locator(".review-screen").count() == 1, "Legacy chapter review did not migrate")
    values = page.evaluate(
        "(keys) => ({ current: window.localStorage.getItem(keys.current), legacy: window.localStorage.getItem(keys.legacy) })",
        {"current": save_key, "legacy": LEGACY_SAVE_KEY},
    )
    assert_condition(values["current"] is not None, "Namespaced save was not written")
    assert_condition(values["legacy"] is None, "Legacy save was cleared before/without successful migration")
    payload = json.loads(values["current"])
    assert_condition(payload["schema_version"] == "narrative_save_v1", "Migrated save uses wrong schema")

    page.evaluate(
        "(keys) => { window.localStorage.removeItem(keys.current); window.localStorage.setItem(keys.legacy, 'not-json'); }",
        {"current": save_key, "legacy": LEGACY_SAVE_KEY},
    )
    page.reload(wait_until="networkidle")
    notice = page.locator('[data-notice="save-recovery"]')
    assert_condition(notice.count() == 1 and "旧进度内容损坏" in notice.inner_text(), "Corrupt legacy fallback is not visible")
    return {"legacy_v1_v2": True, "write_then_clear": True, "visible_corrupt_fallback": True}


def verify_pack_save_isolation(page: Any, base_url: str, save_key: str, assert_condition: Any) -> dict[str, Any]:
    other_key = "narrative_trace.save.other_story.9.9.9"
    page.goto(base_url, wait_until="networkidle")
    page.evaluate("window.localStorage.clear()")
    page.evaluate("(key) => window.localStorage.setItem(key, 'other-pack')", other_key)
    page.reload(wait_until="networkidle")
    values = page.evaluate(
        "(keys) => ({ current: window.localStorage.getItem(keys.current), other: window.localStorage.getItem(keys.other) })",
        {"current": save_key, "other": other_key},
    )
    assert_condition(values["current"] is not None, "Current pack save key was not written")
    assert_condition(values["other"] == "other-pack", "Loading one pack changed another pack's save")
    return {"key": save_key, "other_pack_preserved": True}


def verify_keyboard_and_viewports(browser: Any, page: Any, base_url: str, assert_condition: Any, assert_no_overflow: Any) -> dict[str, Any]:
    page.goto(base_url, wait_until="networkidle")
    page.evaluate("window.localStorage.clear()")
    page.reload(wait_until="networkidle")
    page.keyboard.press("Tab")
    assert_condition(page.evaluate("document.activeElement.id") == "mapButton", "Map button is not first keyboard target")
    page.keyboard.press("Enter")
    assert_condition(page.locator("#pathPanel").get_attribute("aria-hidden") == "false", "Keyboard did not open path map")
    page.keyboard.press("Escape")
    assert_condition(page.evaluate("document.activeElement.id") == "mapButton", "Path map did not return focus")
    assert_no_overflow(page)

    desktop = browser.new_page(viewport={"width": 1280, "height": 900})
    desktop.goto(base_url, wait_until="networkidle")
    assert_no_overflow(desktop)
    assert_condition(desktop.locator("#pathPanel").get_attribute("aria-hidden") == "false", "Desktop path map should be exposed")
    desktop.close()
    return {"keyboard": True, "mobile": [390, 844], "desktop": [1280, 900]}


def verify_surface_fallbacks(browser: Any, base_url: str, context: ContentPackContext, assert_condition: Any) -> list[str]:
    verified: list[str] = []
    for surface_type in ("image", "html"):
        manifest = copy.deepcopy(context.manifest)
        game = copy.deepcopy(context.game)
        surface = game["scenes"][0]["surfaces"][0]
        surface["type"] = surface_type
        surface["fallback"] = {"text": f"{surface_type} fallback is visible <script>never executes</script>"}
        if surface_type == "image":
            surface["content"] = {"asset": "assets/fallback.png", "alt": "fallback fixture"}
        else:
            surface["content"] = {
                "asset": "assets/fallback.html",
                "accessible_name": "fallback fixture",
                "security_profile": "static_sanitized_v1",
            }
        page = browser.new_page(viewport={"width": 390, "height": 844}, is_mobile=True)
        route_pack_documents(page, manifest, game)
        page.goto(base_url, wait_until="networkidle")
        fallback = page.locator(f'.surface-fallback[data-fallback-for="{surface_type}"]')
        assert_condition(fallback.count() == 1, f"{surface_type} fallback did not render")
        assert_condition("never executes" in fallback.inner_text(), f"{surface_type} fallback text missing")
        assert_condition(page.locator("script", has_text="never executes").count() == 0, "Fallback HTML was executed as markup")
        first_anchor = surface["anchors"][0]["id"]
        page.locator(f'button[data-anchor-id="{first_anchor}"]').click()
        assert_condition(page.locator(f'.evidence-card[data-anchor-id="{first_anchor}"]').count() == 1, "Fallback anchor is not interactive")
        page.close()
        verified.append(surface_type)
    return verified


def verify_experimental_notice(browser: Any, base_url: str, context: ContentPackContext, assert_condition: Any) -> dict[str, Any]:
    manifest = copy.deepcopy(context.manifest)
    manifest["loop_package"]["tier"] = "experimental"
    manifest["loop_package"]["verification_status"] = "experimental"
    manifest["experimental_notice"] = True
    page = browser.new_page(viewport={"width": 390, "height": 844}, is_mobile=True)
    route_pack_documents(page, manifest, context.game)
    page.goto(base_url, wait_until="networkidle")
    assert_condition(page.locator('[data-notice="experimental"]').count() == 1, "Experimental notice missing")
    assert_condition(page.locator("[data-anchor-id]").count() == 0, "Experimental content started before acknowledgement")
    page.locator('[data-action="acknowledge-experimental"]').click()
    assert_condition(page.locator("[data-anchor-id]").count() > 0, "Experimental content did not start after acknowledgement")
    page.close()
    return {"blocking_notice": True, "acknowledgement_required": True}


def route_pack_documents(page: Any, manifest: dict[str, Any], game: dict[str, Any]) -> None:
    def fulfill_manifest(route: Any) -> None:
        route.fulfill(status=200, content_type="application/json", body=json.dumps(manifest, ensure_ascii=False))

    def fulfill_game(route: Any) -> None:
        route.fulfill(status=200, content_type="application/json", body=json.dumps(game, ensure_ascii=False))

    page.route("**/content_packs/**/pack.json", fulfill_manifest)
    page.route("**/content_packs/**/game.json", fulfill_game)


def continue_review(page: Any) -> None:
    button = page.locator('[data-action="continue-review"]')
    if button.count():
        button.click()
