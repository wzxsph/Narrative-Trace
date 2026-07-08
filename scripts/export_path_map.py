#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from gamegen.validator import build_path_map, load_game


def main() -> None:
    parser = argparse.ArgumentParser(description="Export path map data from generated game JSON.")
    parser.add_argument("game_json", help="Path to generated game.json")
    parser.add_argument("--out", default="", help="Output path. Defaults to stdout.")
    args = parser.parse_args()
    path_map = build_path_map(load_game(args.game_json))
    payload = json.dumps(path_map, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        Path(args.out).write_text(payload, encoding="utf-8")
    else:
        print(payload)


if __name__ == "__main__":
    main()
