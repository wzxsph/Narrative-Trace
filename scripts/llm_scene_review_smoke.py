#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from gamegen.llm_client import LLMClient, LLMConfig
from gamegen.llm_scene_review import review_scene_artifact_with_llm


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a minimal .env-backed LLM scene artifact review.")
    parser.add_argument("--artifacts", default="generated/missing_phone_agent_v0/scene_artifacts.json")
    parser.add_argument("--blueprint", default="generated/missing_phone_agent_v0/scene_blueprint.json")
    parser.add_argument("--scene-id", default=None)
    parser.add_argument("--out", default=None)
    args = parser.parse_args()

    config = LLMConfig.from_env()
    if config is None:
        print("LLM scene review failed: missing LLM_BASE_URL or LLM_API_KEY in .env", file=sys.stderr)
        return 1

    scene_artifacts = json.loads(Path(args.artifacts).read_text(encoding="utf-8"))
    scene_blueprint = json.loads(Path(args.blueprint).read_text(encoding="utf-8"))
    try:
        review = review_scene_artifact_with_llm(
            scene_artifacts,
            scene_blueprint,
            LLMClient(config),
            scene_id=args.scene_id,
        )
    except Exception as exc:  # noqa: BLE001 - CLI should return provider/model errors as stderr
        print(f"LLM scene review failed: {exc}", file=sys.stderr)
        return 1

    if args.out:
        Path(args.out).write_text(json.dumps(review, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"LLM scene review passed: scene_id={review['scene_id']} verdict={review['verdict']} model={config.model}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
