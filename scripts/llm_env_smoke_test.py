#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from gamegen.llm_client import LLMClient, LLMConfig


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a minimal .env-backed LLM connectivity smoke test.")
    parser.add_argument(
        "--expected",
        default="game_writer_llm_smoke_ok",
        help="Expected JSON value for the ok field.",
    )
    args = parser.parse_args()

    config = LLMConfig.from_env()
    if config is None:
        print("LLM smoke failed: missing LLM_BASE_URL or LLM_API_KEY in .env", file=sys.stderr)
        return 1

    client = LLMClient(config)
    system_prompt = "Return JSON only. No markdown. No prose."
    user_prompt = (
        "Return exactly this JSON object with no extra keys: "
        f'{{"ok":"{args.expected}"}}'
    )

    try:
        result = client.complete_json(system_prompt, user_prompt)
    except Exception as exc:  # noqa: BLE001 - smoke test should report provider shape/errors clearly
        print(f"LLM smoke failed: {exc}", file=sys.stderr)
        return 1

    if result != {"ok": args.expected}:
        print(f"LLM smoke failed: unexpected JSON response shape: {result}", file=sys.stderr)
        return 1

    print(f"LLM smoke passed: model={config.model}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
