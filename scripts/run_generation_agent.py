#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from gamegen.agent_graph import AgentRunError, run_generation_agent


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the graph-based game generation agent.")
    parser.add_argument("--brief", default="examples/briefs/missing_phone.json", help="Path to project brief JSON.")
    parser.add_argument("--out", default="generated/missing_phone_agent_v0", help="Output directory.")
    parser.add_argument(
        "--provider",
        choices=["auto", "offline", "llm"],
        default="auto",
        help="auto uses OpenAI-compatible API when env is configured, otherwise skips LLM polish.",
    )
    parser.add_argument(
        "--max-repair-attempts",
        type=int,
        default=1,
        help="Maximum conservative repair attempts before failing the graph run.",
    )
    args = parser.parse_args()

    try:
        state = run_generation_agent(
            brief_path=args.brief,
            out_dir=args.out,
            provider=args.provider,
            max_repair_attempts=args.max_repair_attempts,
        )
    except AgentRunError as exc:
        print(f"Generation agent failed: {exc}", file=sys.stderr)
        return 1

    print(f"Generation agent exported artifacts at {args.out}")
    print(f"- trace_events: {len(state.trace_events)}")
    print(f"- repair_attempts: {state.repair_attempts}")
    print(f"- repairs: {len(state.repairs)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
