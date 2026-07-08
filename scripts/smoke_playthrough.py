#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class SmokeRuntime:
    def __init__(self, game: dict):
        self.game = game
        self.scene_id = game["start_scene_id"]
        self.state = dict(game.get("initial_state", {}))
        self.opened: set[str] = set()
        self.choices: list[str] = []
        self.ending_id = ""

    def open_anchor(self, anchor_id: str) -> None:
        anchor = self.find_anchor(anchor_id)
        if not anchor:
            raise AssertionError(f"Anchor not found: {anchor_id}")
        self.opened.add(anchor_id)
        self.apply_effects(anchor.get("effects", []))

    def choose(self, choice_id: str) -> None:
        scene = self.current_scene()
        choice = next((item for item in scene["choices"] if item["id"] == choice_id), None)
        if not choice:
            raise AssertionError(f"Choice not found in current scene: {choice_id}")
        if not all(self.matches(requirement) for requirement in choice.get("requirements", [])):
            raise AssertionError(f"Choice requirements not met: {choice_id}")
        self.apply_effects(choice.get("effects", []))
        self.choices.append(choice_id)
        target = choice["next_scene"]
        if any(ending["id"] == target for ending in self.game.get("endings", [])):
            self.ending_id = target
        else:
            self.scene_id = target

    def current_scene(self) -> dict:
        return next(scene for scene in self.game["scenes"] if scene["id"] == self.scene_id)

    def matches(self, requirement: dict) -> bool:
        value = self.state.get(requirement["state"])
        if "equals" in requirement:
            return value == requirement["equals"]
        if "min" in requirement:
            return float(value or 0) >= float(requirement["min"])
        return bool(value)

    def apply_effects(self, effects: list[dict]) -> None:
        for effect in effects:
            for key, value in effect.get("set", {}).items():
                self.state[key] = value
            for key, value in effect.get("add", {}).items():
                self.state[key] = float(self.state.get(key, 0)) + float(value)

    def find_anchor(self, anchor_id: str) -> dict | None:
        for scene in self.game["scenes"]:
            for block in scene.get("background_blocks", []):
                for anchor in block.get("observe_anchors", []):
                    found = self.find_anchor_in_tree(anchor, anchor_id)
                    if found:
                        return found
        return None

    def find_anchor_in_tree(self, anchor: dict, anchor_id: str) -> dict | None:
        if anchor["id"] == anchor_id:
            return anchor
        for child in anchor.get("opens_fragment", {}).get("nested_anchors", []):
            found = self.find_anchor_in_tree(child, anchor_id)
            if found:
                return found
        return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a deterministic smoke playthrough.")
    parser.add_argument("game_json", help="Path to generated game.json")
    args = parser.parse_args()
    game = json.loads(Path(args.game_json).read_text(encoding="utf-8"))
    runtime = SmokeRuntime(game)
    runtime.open_anchor("obs_unsent_sms")
    runtime.open_anchor("obs_0213_log")
    runtime.choose("choice_go_station")
    runtime.open_anchor("obs_ticket")
    runtime.open_anchor("obs_locker_code")
    runtime.choose("choice_open_locker")
    runtime.open_anchor("obs_raw_recording")
    runtime.choose("choice_publish_truth")
    if runtime.ending_id != "ending_publish":
        raise AssertionError(f"Expected ending_publish, got {runtime.ending_id}")
    print("Smoke playthrough passed: choice_go_station -> choice_open_locker -> ending_publish")


if __name__ == "__main__":
    main()

