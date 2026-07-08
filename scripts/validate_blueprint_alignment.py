#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from gamegen.blueprint_alignment import validate_blueprint_alignment


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate that game.json satisfies scene_blueprint.json.")
    parser.add_argument("game", help="Path to game.json")
    parser.add_argument("--blueprint", default=None, help="Path to scene_blueprint.json")
    args = parser.parse_args()

    game_path = Path(args.game)
    blueprint_path = Path(args.blueprint) if args.blueprint else game_path.with_name("scene_blueprint.json")
    game = json.loads(game_path.read_text(encoding="utf-8"))
    blueprint = json.loads(blueprint_path.read_text(encoding="utf-8"))

    messages = validate_blueprint_alignment(game, blueprint)
    errors = [message for message in messages if message.level == "error"]

    if not messages:
        print(f"OK: {game_path} satisfies {blueprint_path}")
        return 0

    for message in messages:
        print(f"{message.level.upper()} {message.location}: {message.message}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
