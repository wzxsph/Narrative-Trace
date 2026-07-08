#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from gamegen.state_schema_design import validate_state_schema_design


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a generated state_schema_design.json artifact.")
    parser.add_argument("path", help="Path to state_schema_design.json")
    args = parser.parse_args()

    path = Path(args.path)
    design = json.loads(path.read_text(encoding="utf-8"))
    messages = validate_state_schema_design(design)
    errors = [message for message in messages if message.level == "error"]

    if not messages:
        print(f"OK: {path} passed state schema design validation")
        return 0

    for message in messages:
        print(f"{message.level.upper()} {message.location}: {message.message}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
