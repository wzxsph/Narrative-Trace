from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
LOOP_PACKAGES_ROOT = ROOT / "loop_packages"


class ContentPackLoadError(ValueError):
    pass


@dataclass(frozen=True)
class ContentPackContext:
    root: Path
    manifest: dict[str, Any]
    game: dict[str, Any]
    state_registry: dict[str, Any]
    provenance: dict[str, Any]
    loop_root: Path
    loop_manifest: dict[str, Any]
    loop_schema_extension: dict[str, Any]
    loop_acceptance_rules: dict[str, Any]
    loop_experience_metrics: dict[str, Any]


def load_content_pack(pack_dir: str | Path) -> ContentPackContext:
    root = Path(pack_dir).resolve()
    if not root.is_dir():
        raise ContentPackLoadError(f"Content pack directory not found: {root}")
    manifest = load_json_file(root / "pack.json", "pack manifest")
    entrypoints = manifest.get("entrypoints")
    if not isinstance(entrypoints, dict):
        raise ContentPackLoadError("pack.entrypoints must be an object")
    game = load_json_file(resolve_relative_file(root, entrypoints.get("game"), "pack.entrypoints.game"), "game")
    state_registry = load_json_file(
        resolve_relative_file(root, entrypoints.get("state_registry"), "pack.entrypoints.state_registry"),
        "state registry",
    )
    provenance = load_json_file(
        resolve_relative_file(root, entrypoints.get("provenance"), "pack.entrypoints.provenance"),
        "provenance",
    )

    loop_ref = manifest.get("loop_package")
    if not isinstance(loop_ref, dict):
        raise ContentPackLoadError("pack.loop_package must be an object")
    loop_id = loop_ref.get("id")
    version = loop_ref.get("version")
    if not isinstance(loop_id, str) or not isinstance(version, str):
        raise ContentPackLoadError("pack.loop_package.id and version are required")
    try:
        major = int(version.split(".", 1)[0])
    except (TypeError, ValueError) as exc:
        raise ContentPackLoadError(f"Invalid loop package version: {version}") from exc
    loop_root = (LOOP_PACKAGES_ROOT / loop_id / f"v{major}").resolve()
    expected_parent = LOOP_PACKAGES_ROOT.resolve()
    if not loop_root.is_relative_to(expected_parent) or not loop_root.is_dir():
        raise ContentPackLoadError(f"Loop package not installed: {loop_id}@{version}")
    loop_manifest = load_json_file(loop_root / "loop.json", "loop package manifest")
    loop_entrypoints = loop_manifest.get("entrypoints")
    if not isinstance(loop_entrypoints, dict):
        raise ContentPackLoadError("loop.entrypoints must be an object")

    return ContentPackContext(
        root=root,
        manifest=manifest,
        game=game,
        state_registry=state_registry,
        provenance=provenance,
        loop_root=loop_root,
        loop_manifest=loop_manifest,
        loop_schema_extension=load_json_file(
            resolve_relative_file(loop_root, loop_entrypoints.get("schema_extension"), "loop.entrypoints.schema_extension"),
            "loop schema extension",
        ),
        loop_acceptance_rules=load_json_file(
            resolve_relative_file(loop_root, loop_entrypoints.get("acceptance_rules"), "loop.entrypoints.acceptance_rules"),
            "loop acceptance rules",
        ),
        loop_experience_metrics=load_json_file(
            resolve_relative_file(loop_root, loop_entrypoints.get("experience_metrics"), "loop.entrypoints.experience_metrics"),
            "loop experience metrics",
        ),
    )


def resolve_relative_file(root: Path, relative: Any, label: str) -> Path:
    if not isinstance(relative, str) or not relative:
        raise ContentPackLoadError(f"{label} must be a non-empty relative path")
    candidate = Path(relative)
    if candidate.is_absolute():
        raise ContentPackLoadError(f"{label} must not be absolute")
    resolved = (root / candidate).resolve()
    if not resolved.is_relative_to(root.resolve()):
        raise ContentPackLoadError(f"{label} escapes its package root")
    if not resolved.is_file():
        raise ContentPackLoadError(f"{label} file not found: {relative}")
    return resolved


def load_json_file(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ContentPackLoadError(f"{label} file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ContentPackLoadError(f"{label} is not valid JSON: {exc.msg}") from exc
    if not isinstance(value, dict):
        raise ContentPackLoadError(f"{label} must contain a JSON object")
    return value
