from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import Iterable, Literal

try:
    from .browser_smoke import ROOT, assert_condition, assert_no_horizontal_overflow, chrome_executable, static_server
except ImportError:  # pragma: no cover - supports direct script execution
    from browser_smoke import ROOT, assert_condition, assert_no_horizontal_overflow, chrome_executable, static_server


StepKind = Literal["observe", "choice"]


@dataclass(frozen=True)
class Step:
    kind: StepKind
    target_id: str


@dataclass(frozen=True)
class PathSpec:
    name: str
    expected_ending: str
    expected_title: str
    expected_tags: tuple[str, ...]
    steps: tuple[Step, ...]


PATHS: tuple[PathSpec, ...] = (
    PathSpec(
        name="publish_truth_path",
        expected_ending="ending_publish",
        expected_title="公开的真相",
        expected_tags=("truth_first", "lin_survived", "chen_exposed"),
        steps=(
            Step("observe", "obs_unsent_sms"),
            Step("observe", "obs_0213_log"),
            Step("choice", "choice_go_station"),
            Step("observe", "obs_session_token"),
            Step("choice", "choice_freeze_wipe"),
            Step("observe", "obs_taxi_order"),
            Step("choice", "choice_leave_for_station"),
            Step("observe", "obs_station_entry_code"),
            Step("choice", "choice_enter_service_corridor"),
            Step("observe", "obs_ticket"),
            Step("observe", "obs_locker_code"),
            Step("choice", "choice_open_locker"),
            Step("observe", "obs_backup_drive"),
            Step("choice", "choice_take_backup_to_safehouse"),
            Step("observe", "obs_raw_recording"),
            Step("choice", "choice_compare_context"),
            Step("observe", "obs_victim_list"),
            Step("choice", "choice_prepare_public_packet"),
            Step("observe", "obs_public_packet"),
            Step("choice", "choice_publish_truth"),
        ),
    ),
    PathSpec(
        name="private_archive_path",
        expected_ending="ending_bury",
        expected_title="沉默的备份",
        expected_tags=("protect_person", "truth_buried", "private_archive"),
        steps=(
            Step("choice", "choice_call_chen"),
            Step("observe", "obs_device_admin"),
            Step("choice", "choice_isolate_phone"),
            Step("observe", "obs_voice_note"),
            Step("choice", "choice_send_voice_to_self"),
            Step("observe", "obs_security_booth"),
            Step("choice", "choice_wait_guard_shift"),
            Step("observe", "obs_recording_warning"),
            Step("choice", "choice_read_wall_note"),
            Step("observe", "obs_red_bracelet"),
            Step("choice", "choice_protect_lin_secret"),
            Step("observe", "obs_context_chain"),
            Step("choice", "choice_archive_first"),
            Step("observe", "obs_final_message"),
            Step("choice", "choice_prepare_archive"),
            Step("observe", "obs_offline_archive"),
            Step("choice", "choice_keep_archive"),
        ),
    ),
    PathSpec(
        name="confront_chen_path",
        expected_ending="ending_confront",
        expected_title="被迫摊牌",
        expected_tags=("chen_suspicious", "company_alerted", "unstable_truth"),
        steps=(
            Step("observe", "obs_unsent_sms"),
            Step("observe", "obs_0213_log"),
            Step("observe", "obs_trimmed_gap"),
            Step("choice", "choice_confront_chen"),
            Step("observe", "obs_chen_alias"),
            Step("observe", "obs_casefile_share"),
            Step("choice", "choice_warn_chen"),
            Step("choice", "choice_call_chen_at_gate"),
            Step("observe", "obs_red_dot"),
            Step("choice", "choice_cover_camera"),
            Step("observe", "obs_backup_drive"),
            Step("choice", "choice_take_backup_to_safehouse"),
            Step("observe", "obs_edited_recording"),
            Step("choice", "choice_send_hash_to_chen"),
            Step("observe", "obs_chen_pause"),
            Step("choice", "choice_ask_chen_last_time"),
            Step("observe", "obs_send_to_chen"),
            Step("choice", "choice_confront_final"),
        ),
    ),
)


def click_observe(page: object, anchor_id: str) -> None:
    selector = f'button[data-anchor-id="{anchor_id}"]'
    anchor = page.locator(selector)
    assert_condition(anchor.count() > 0, f"Observe anchor not found: {anchor_id}")
    anchor.first.click()


def click_choice(page: object, choice_id: str) -> None:
    selector = f'button[data-choice-id="{choice_id}"]'
    choice = page.locator(selector)
    assert_condition(choice.count() > 0, f"Choice not visible or not found: {choice_id}")
    choice.first.click()


def continue_if_review(page: object) -> int:
    if page.locator(".review-screen").count() == 0:
        return 0
    review_text = page.locator(".review-screen").inner_text()
    assert_condition("本章路径图" in review_text, "Chapter review did not render flowchart")
    assert_condition("关键行动" in review_text, "Chapter review did not render chosen action")
    assert_condition(page.locator(".chapter-flow-node").count() == 3, "Chapter review should contain 3 flow nodes")
    assert_condition(page.locator('[data-action="continue-review"]').count() == 1, "Continue review button missing")
    assert_no_horizontal_overflow(page)
    page.locator('[data-action="continue-review"]').click()
    return 1


def reset_page(page: object, base_url: str) -> None:
    page.goto(base_url, wait_until="networkidle")
    page.evaluate("window.localStorage.clear()")
    page.reload(wait_until="networkidle")
    page.wait_for_selector('button[data-anchor-id="obs_unsent_sms"]')


def run_path(page: object, base_url: str, path: PathSpec) -> dict[str, object]:
    reset_page(page, base_url)
    reviews_seen = 0
    observed: list[str] = []
    chosen: list[str] = []

    for step in path.steps:
        if step.kind == "observe":
            click_observe(page, step.target_id)
            observed.append(step.target_id)
        else:
            click_choice(page, step.target_id)
            chosen.append(step.target_id)
            reviews_seen += continue_if_review(page)
        assert_no_horizontal_overflow(page)

    page.wait_for_selector(".ending-screen")
    ending_text = page.locator(".ending-screen").inner_text()
    title_text = page.locator("#sceneTitle").inner_text()
    tags = page.locator(".ending-screen .tag").all_inner_texts()
    profile_sections = page.locator(".ending-screen .profile-section h3").all_inner_texts()

    assert_condition(title_text == path.expected_title, f"Unexpected ending title for {path.name}: {title_text}")
    assert_condition(path.expected_title in ending_text, f"Ending body missing title for {path.name}")
    for tag in path.expected_tags:
        assert_condition(tag in tags, f"Ending tag missing for {path.name}: {tag}")
    for section_title in ("关键观察", "关键行动", "最终立场", "结局标签"):
        assert_condition(section_title in profile_sections, f"Ending profile section missing: {section_title}")
    assert_condition(reviews_seen == 2, f"{path.name} should pass two chapter reviews, saw {reviews_seen}")

    return {
        "name": path.name,
        "ending": path.expected_ending,
        "title": title_text,
        "reviews_seen": reviews_seen,
        "observes": len(observed),
        "choices": len(chosen),
        "tags": tags,
    }


def run_browser_e2e_matrix(paths: Iterable[PathSpec] = PATHS) -> list[dict[str, object]]:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:  # pragma: no cover - depends on local environment
        raise RuntimeError("Python package 'playwright' is required for browser E2E matrix") from exc

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
            results = [run_path(page, base_url, path) for path in paths]
            browser.close()
            return results


def main() -> int:
    try:
        results = run_browser_e2e_matrix()
    except Exception as exc:  # noqa: BLE001 - command should print actionable failure
        print(f"Browser E2E matrix failed: {exc}", file=sys.stderr)
        return 1

    print("Browser E2E matrix passed")
    for result in results:
        print(
            f"- {result['ending']}: {result['title']} "
            f"({result['observes']} observes, {result['choices']} choices, {result['reviews_seen']} reviews)"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
