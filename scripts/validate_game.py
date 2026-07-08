#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from gamegen.validator import load_game, validate_game


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate a generated text adventure game JSON.")
    parser.add_argument("game_json", help="Path to generated game.json")
    args = parser.parse_args()
    messages = validate_game(load_game(args.game_json))
    for message in messages:
        print(f"[{message.level.upper()}] {message.location}: {message.message}")
    if any(message.level == "error" for message in messages):
        sys.exit(1)
    print("Validation passed without errors")


if __name__ == "__main__":
    main()
