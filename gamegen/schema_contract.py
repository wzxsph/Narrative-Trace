from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCHEMA = ROOT / "schemas" / "game.schema.json"


def load_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_default_schema() -> dict[str, Any]:
    return load_json(DEFAULT_SCHEMA)


def validate_against_schema(instance: Any, schema: dict[str, Any]) -> list[str]:
    try:
        from jsonschema import Draft202012Validator
    except ImportError as exc:  # pragma: no cover - environment guard
        raise RuntimeError("Python package 'jsonschema' is required for schema validation") from exc

    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(instance), key=lambda item: list(item.absolute_path))
    return [format_error(error) for error in errors]


def validate_against_default_schema(instance: Any) -> list[str]:
    return validate_against_schema(instance, load_default_schema())


def format_error(error: Any) -> str:
    path = ".".join(str(part) for part in error.absolute_path)
    location = path or "<root>"
    return f"{location}: {error.message}"
