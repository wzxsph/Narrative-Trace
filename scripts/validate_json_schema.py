#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCHEMA = ROOT / "schemas" / "game.schema.json"


def load_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def validate_against_schema(instance: Any, schema: dict[str, Any]) -> list[str]:
    try:
        from jsonschema import Draft202012Validator
    except ImportError as exc:  # pragma: no cover - environment guard
        raise RuntimeError("Python package 'jsonschema' is required for schema validation") from exc

    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(instance), key=lambda item: list(item.absolute_path))
    return [format_error(error) for error in errors]


def format_error(error: Any) -> str:
    path = ".".join(str(part) for part in error.absolute_path)
    location = path or "<root>"
    return f"{location}: {error.message}"


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
