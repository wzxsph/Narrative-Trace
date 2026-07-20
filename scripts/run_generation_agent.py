#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from gamegen.agent_graph import AgentRunError, run_generation_agent
from gamegen.v1_agent import (
    V1AgentError,
    advance_pipeline,
    approve_pipeline_checkpoint,
    build_release_bundle,
    prepare_pipeline,
)


V1_COMMANDS = {"prepare", "approve", "continue", "bundle", "status"}


def main(argv: list[str] | None = None) -> int:
    values = list(sys.argv[1:] if argv is None else argv)
    if not values or values[0] in V1_COMMANDS or values[0] in {"-h", "--help"}:
        return v1_main(values)
    return legacy_main(values)


def v1_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Run the staged Framework V1 content-pack agent.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare = subparsers.add_parser("prepare", help="Stage a brief and pause for brief approval.")
    prepare.add_argument("--brief", required=True)
    prepare.add_argument("--out", required=True, help="Content-pack workspace/output directory")
    prepare.add_argument("--loop", default="investigation@1.0.0")
    prepare.add_argument("--pack-version", default="1.0.0")
    prepare.add_argument("--provider", choices=["auto", "offline", "llm"], default="offline")
    prepare.add_argument("--max-repair-attempts", type=int, default=1)

    approve = subparsers.add_parser("approve", help="Write a digest-bound human DecisionReceipt.")
    approve.add_argument("--out", required=True)
    approve.add_argument(
        "--checkpoint",
        required=True,
        choices=["brief", "blueprint", "release", "playtest_attribution"],
    )
    approve.add_argument("--actor", required=True)
    approve.add_argument("--notes", default="")
    approve.add_argument(
        "--decision",
        choices=["approved", "rejected", "content_issue", "loop_issue", "inconclusive"],
        default="approved",
    )
    approve.add_argument("--experimental-opt-in", action="store_true")
    approve.add_argument("--subject", help="Required external subject for playtest attribution")

    advance = subparsers.add_parser("continue", help="Advance exactly one approved pipeline phase.")
    advance.add_argument("--out", required=True)
    advance.add_argument("--gate-through", choices=["G4", "G5"], default="G5")

    bundle = subparsers.add_parser("bundle", help="Build, but do not deploy, an approved release bundle.")
    bundle.add_argument("--out", required=True, help="Content-pack workspace")
    bundle.add_argument("--bundle-out", required=True)
    bundle.add_argument("--format", choices=["static", "worker"], default="static")

    status = subparsers.add_parser("status", help="Print the current staged pipeline state.")
    status.add_argument("--out", required=True)

    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            pipeline = prepare_pipeline(
                args.brief,
                args.out,
                loop_ref=args.loop,
                provider=args.provider,
                pack_version=args.pack_version,
                max_repair_attempts=args.max_repair_attempts,
            )
        elif args.command == "approve":
            receipt = approve_pipeline_checkpoint(
                args.out,
                args.checkpoint,
                actor=args.actor,
                notes=args.notes,
                decision=args.decision,
                experimental_opt_in=args.experimental_opt_in,
                subject_path=args.subject,
            )
            print(json.dumps(receipt, ensure_ascii=False, indent=2))
            return 0
        elif args.command == "continue":
            pipeline = advance_pipeline(args.out, gate_through=args.gate_through)
        elif args.command == "bundle":
            record = build_release_bundle(args.out, args.bundle_out, bundle_format=args.format)
            print(json.dumps(record, ensure_ascii=False, indent=2))
            return 0
        else:
            pipeline_path = Path(args.out) / "pipeline.json"
            pipeline = json.loads(pipeline_path.read_text(encoding="utf-8"))
    except (V1AgentError, FileNotFoundError, json.JSONDecodeError) as exc:
        print(f"Framework V1 agent paused/failed: {exc}", file=sys.stderr)
        return 1

    print(json.dumps({"phase": pipeline["phase"], "digests": pipeline.get("digests", {})}, ensure_ascii=False, indent=2))
    return 0


def legacy_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Deprecated V0 projection CLI. Use 'prepare/approve/continue/bundle' for Framework V1."
    )
    parser.add_argument("--brief", default="examples/briefs/missing_phone.json", help="Path to project brief JSON.")
    parser.add_argument("--out", default="generated/missing_phone_agent_v0", help="Output directory.")
    parser.add_argument(
        "--provider",
        choices=["auto", "offline", "llm"],
        default="auto",
        help="auto uses OpenAI-compatible API when env is configured, otherwise skips LLM polish.",
    )
    parser.add_argument("--max-repair-attempts", type=int, default=1)
    args = parser.parse_args(argv)
    print(
        "DEPRECATED: the V0 CLI is a read-only compatibility projection and will not be removed before separately approved V1.1.",
        file=sys.stderr,
    )
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
    print(f"Generation agent exported deprecated V0 projection at {args.out}")
    print(f"- trace_events: {len(state.trace_events)}")
    print(f"- repair_attempts: {state.repair_attempts}")
    print(f"- repairs: {len(state.repairs)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
