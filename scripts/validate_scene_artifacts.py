#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from gamegen.scene_artifacts import validate_scene_artifacts


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate scene_artifacts.json against scene_blueprint.json.")
    parser.add_argument("path", help="Path to scene_artifacts.json")
    parser.add_argument("--blueprint", default=None, help="Path to scene_blueprint.json")
    args = parser.parse_args()

    path = Path(args.path)
    blueprint_path = Path(args.blueprint) if args.blueprint else path.with_name("scene_blueprint.json")
    scene_artifacts = json.loads(path.read_text(encoding="utf-8"))
    scene_blueprint = json.loads(blueprint_path.read_text(encoding="utf-8"))

    messages = validate_scene_artifacts(scene_artifacts, scene_blueprint)
    errors = [message for message in messages if message.level == "error"]

    if not messages:
        print(f"OK: {path} passed scene artifact validation")
        return 0

    for message in messages:
        print(f"{message.level.upper()} {message.location}: {message.message}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
