#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from gamegen.review_issues import validate_review_issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate review_issues.json.")
    parser.add_argument("path", help="Path to review_issues.json")
    args = parser.parse_args()

    path = Path(args.path)
    review_issues = json.loads(path.read_text(encoding="utf-8"))
    messages = validate_review_issues(review_issues)
    errors = [message for message in messages if message.level == "error"]

    if not messages:
        print(f"OK: {path} passed review issue validation")
        return 0

    for message in messages:
        print(f"{message.level.upper()} {message.location}: {message.message}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
