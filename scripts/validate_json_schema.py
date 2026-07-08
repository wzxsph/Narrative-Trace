#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from gamegen.schema_contract import DEFAULT_SCHEMA, load_json, validate_against_schema


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate game JSON against the explicit JSON Schema contract.")
    parser.add_argument("game_json", help="Path to generated game.json")
    parser.add_argument("--schema", default=str(DEFAULT_SCHEMA), help="Path to JSON Schema")
    args = parser.parse_args()

    instance = load_json(args.game_json)
    schema = load_json(args.schema)
    errors = validate_against_schema(instance, schema)
    if errors:
        print("JSON schema validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("JSON schema validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
