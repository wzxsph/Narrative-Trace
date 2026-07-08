#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from gamegen.validator import load_game, validate_game


def main() -> None:
    parser = argparse.ArgumentParser(description="Report repair targets for a generated game.")
    parser.add_argument("game_json", help="Path to generated game.json")
    args = parser.parse_args()
    messages = validate_game(load_game(args.game_json))
    errors = [message for message in messages if message.level == "error"]
    if not errors:
        print("No repair needed: validation has no errors")
        return
    print("Repair loop V0 is conservative. Fix these local errors before generation can continue:")
    for message in errors:
        print(f"- {message.location}: {message.message}")


if __name__ == "__main__":
    main()
