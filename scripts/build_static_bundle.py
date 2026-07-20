#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from gamegen.content_pack import ContentPackContext, load_content_pack, resolve_relative_file
from gamegen.gates import run_pack_gates


def build_static_bundle(pack_dir: str | Path, output_dir: str | Path) -> dict[str, Any]:
    context = load_content_pack(pack_dir)
    gate_results = run_pack_gates(context.root, through="G4")
    if any(result.status != "passed" for result in gate_results):
        failed = next(result for result in gate_results if result.status != "passed")
        raise ValueError(f"{failed.gate_id} failed; refusing to build")

    output = Path(output_dir).resolve()
    assert_safe_output(output, context.root)
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)

    copy_file(ROOT / "index.html", output / "index.html")
    shutil.copytree(ROOT / "src", output / "src")
    (output / ".nojekyll").touch()

    relative_pack_root = Path("content_packs") / context.manifest["pack_id"] / context.manifest["version"]
    destination_pack = output / relative_pack_root
    included = collect_pack_files(context)
    for source in included:
        copy_file(source, destination_pack / source.relative_to(context.root))

    runtime_config = {
        "schema_version": "narrative_runtime_config_v1",
        "runtime_version": "1.0.0",
        "pack": relative_pack_root.as_posix(),
    }
    (output / "runtime-config.json").write_text(
        json.dumps(runtime_config, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return {
        "pack": f"{context.manifest['pack_id']}@{context.manifest['version']}",
        "output": str(output),
        "files": sorted(path.relative_to(context.root).as_posix() for path in included),
        "gates": [result.gate_id for result in gate_results],
    }


def collect_pack_files(context: ContentPackContext) -> set[Path]:
    files = {context.root / "pack.json"}
    for label, relative in context.manifest["entrypoints"].items():
        files.add(resolve_relative_file(context.root, relative, f"pack.entrypoints.{label}"))
    for artifact in context.provenance.get("artifacts", []):
        files.add(resolve_relative_file(context.root, artifact["path"], "provenance.artifacts.path"))
    for asset in iter_surface_assets(context.game):
        files.add(resolve_relative_file(context.root, asset, "surface.content.asset"))
    return files


def iter_surface_assets(game: dict[str, Any]) -> Iterable[str]:
    for scene in game.get("scenes", []):
        for surface in scene.get("surfaces", []):
            yield from iter_assets_from_surface(surface)


def iter_assets_from_surface(surface: dict[str, Any]) -> Iterable[str]:
    if surface.get("type") in {"image", "html"}:
        asset = surface.get("content", {}).get("asset")
        if isinstance(asset, str):
            yield asset
    for anchor in surface.get("anchors", []):
        for child in anchor.get("fragment", {}).get("surfaces", []):
            yield from iter_assets_from_surface(child)


def assert_safe_output(output: Path, pack_root: Path) -> None:
    forbidden = {Path("/").resolve(), ROOT.resolve(), pack_root.resolve(), Path.home().resolve()}
    if output in forbidden or len(output.parts) < 3:
        raise ValueError(f"Unsafe bundle output directory: {output}")


def copy_file(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build one Framework V1 pack as a static site.")
    parser.add_argument("--pack", required=True, help="Content pack directory containing pack.json")
    parser.add_argument("--output", required=True, help="Clean output directory")
    args = parser.parse_args(argv)
    try:
        result = build_static_bundle(args.pack, args.output)
    except Exception as exc:  # noqa: BLE001 - CLI reports configuration errors
        print(f"Static bundle failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
