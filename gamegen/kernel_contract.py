from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
KERNEL_SCHEMA_DIR = ROOT / "schemas" / "kernel" / "v1"


def load_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_kernel_schemas() -> dict[str, dict[str, Any]]:
    schemas: dict[str, dict[str, Any]] = {}
    for path in sorted(KERNEL_SCHEMA_DIR.glob("*.schema.json")):
        schema = load_json(path)
        schemas[path.name] = schema
    return schemas


def validate_kernel_document(schema_name: str, instance: Any) -> list[str]:
    schemas = load_kernel_schemas()
    if schema_name not in schemas:
        raise ValueError(f"Unknown Kernel schema: {schema_name}")
    try:
        from jsonschema import Draft202012Validator
        from referencing import Registry, Resource
    except ImportError as exc:  # pragma: no cover - environment guard
        raise RuntimeError("Python packages 'jsonschema' and 'referencing' are required") from exc

    registry = Registry()
    for schema in schemas.values():
        resource = Resource.from_contents(schema)
        registry = registry.with_resource(schema["$id"], resource)
        filename_uri = schema["$id"].rsplit("/", 1)[0] + "/" + schema["$id"].rsplit("/", 1)[1]
        registry = registry.with_resource(filename_uri, resource)

    validator = Draft202012Validator(schemas[schema_name], registry=registry)
    errors = sorted(validator.iter_errors(instance), key=lambda item: [str(part) for part in item.absolute_path])
    return [_format_error(error) for error in errors]


def validate_kernel_definition(schema_name: str, definition: str, instance: Any) -> list[str]:
    schemas = load_kernel_schemas()
    schema = schemas.get(schema_name)
    if schema is None:
        raise ValueError(f"Unknown Kernel schema: {schema_name}")
    definition_schema = schema.get("$defs", {}).get(definition)
    if definition_schema is None:
        raise ValueError(f"Unknown definition '{definition}' in {schema_name}")
    wrapper = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": f"https://narrative-trace.dev/schemas/kernel/v1/_definition_{schema_name}_{definition}.json",
        "$ref": f"{schema['$id']}#/$defs/{definition}",
    }
    try:
        from jsonschema import Draft202012Validator
        from referencing import Registry, Resource
    except ImportError as exc:  # pragma: no cover - environment guard
        raise RuntimeError("Python packages 'jsonschema' and 'referencing' are required") from exc
    registry = Registry()
    for item in schemas.values():
        registry = registry.with_resource(item["$id"], Resource.from_contents(item))
    registry = registry.with_resource(wrapper["$id"], Resource.from_contents(wrapper))
    validator = Draft202012Validator(wrapper, registry=registry)
    errors = sorted(validator.iter_errors(instance), key=lambda item: [str(part) for part in item.absolute_path])
    return [_format_error(error) for error in errors]


def canonical_digest(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def file_digest(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _format_error(error: Any) -> str:
    path = ".".join(str(part) for part in error.absolute_path)
    return f"{path or '<root>'}: {error.message}"
