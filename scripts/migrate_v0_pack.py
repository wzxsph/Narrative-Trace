#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from gamegen.v1_migration import export_v1_content_pack


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert one legacy V0 game.json into a Framework V1 content pack.")
    parser.add_argument("source", help="Legacy game.json path")
    parser.add_argument("out", help="V1 content pack directory")
    args = parser.parse_args()
    source = Path(args.source)
    if not source.is_file():
        print(f"Legacy game not found: {source}", file=sys.stderr)
        return 2
    game = json.loads(source.read_text(encoding="utf-8"))
    export_v1_content_pack(game, args.out)
    print(f"Migrated Framework V1 content pack to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
