#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from gamegen.demo_agent import export_game, generate_game, load_brief


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a demo text adventure game.")
    parser.add_argument("--brief", default="examples/briefs/missing_phone.json", help="Path to project brief JSON.")
    parser.add_argument("--out", default="generated/missing_phone_v0", help="Output directory.")
    parser.add_argument(
        "--provider",
        choices=["auto", "offline", "llm"],
        default="auto",
        help="auto uses OpenAI-compatible API when env is configured, otherwise offline.",
    )
    args = parser.parse_args()
    brief = load_brief(args.brief)
    game = generate_game(brief, provider=args.provider)
    export_game(game, Path(args.out))
    print(f"Generated demo game at {args.out}")


if __name__ == "__main__":
    main()
