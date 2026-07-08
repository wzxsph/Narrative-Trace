#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from gamegen.scene_blueprint import validate_scene_blueprint_design


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a generated scene_blueprint.json artifact.")
    parser.add_argument("path", help="Path to scene_blueprint.json")
    parser.add_argument("--plan", default=None, help="Path to generation_plan.json")
    parser.add_argument("--state-schema", default=None, help="Path to state_schema_design.json")
    args = parser.parse_args()

    path = Path(args.path)
    plan_path = Path(args.plan) if args.plan else path.with_name("generation_plan.json")
    state_schema_path = Path(args.state_schema) if args.state_schema else path.with_name("state_schema_design.json")

    blueprint = json.loads(path.read_text(encoding="utf-8"))
    generation_plan = json.loads(plan_path.read_text(encoding="utf-8"))
    state_schema_design = json.loads(state_schema_path.read_text(encoding="utf-8"))

    messages = validate_scene_blueprint_design(blueprint, generation_plan, state_schema_design)
    errors = [message for message in messages if message.level == "error"]

    if not messages:
        print(f"OK: {path} passed scene blueprint validation")
        return 0

    for message in messages:
        print(f"{message.level.upper()} {message.location}: {message.message}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
