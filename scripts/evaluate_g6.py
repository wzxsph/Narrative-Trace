#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from gamegen.g6 import G6ConfigError, apply_g6_outcome, run_g6
from gamegen.decision_receipt import DecisionReceiptError, create_decision_receipt, write_receipt
from gamegen.model_output_archive import assert_no_unredacted_secrets


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate or apply Framework V1 G6 playtest evidence.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    evaluate = subparsers.add_parser("evaluate", help="Recompute G6 from anonymous per-player records.")
    evaluate.add_argument("--pack", required=True)
    evaluate.add_argument("--batch", required=True)
    evaluate.add_argument("--out", required=True, help="GateResult JSON output")
    apply = subparsers.add_parser("apply", help="Apply a current G6 result to loop/package tiers.")
    apply.add_argument("--pack", required=True)
    apply.add_argument("--batch", required=True)
    apply.add_argument("--report", required=True)
    apply.add_argument("--attribution-receipt")
    attribute = subparsers.add_parser("attribute", help="Bind a human attribution decision to a failed G6 report.")
    attribute.add_argument("--report", required=True)
    attribute.add_argument("--out", required=True)
    attribute.add_argument("--actor", required=True)
    attribute.add_argument("--decision", required=True, choices=["content_issue", "loop_issue", "inconclusive"])
    attribute.add_argument("--notes", default="")
    args = parser.parse_args(argv)
    try:
        if args.command == "evaluate":
            result = run_g6(args.pack, args.batch)
            payload = result.to_dict()
            output = Path(args.out)
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            return 0 if result.status == "passed" else 1
        if args.command == "attribute":
            receipt = create_decision_receipt(
                checkpoint="playtest_attribution",
                subject_path=args.report,
                actor=args.actor,
                decision=args.decision,
                notes=args.notes,
            )
            rendered = json.dumps(receipt, ensure_ascii=False, indent=2)
            assert_no_unredacted_secrets(rendered)
            write_receipt(args.out, receipt)
            print(rendered)
            return 0
        applied = apply_g6_outcome(args.pack, args.batch, args.report, attribution_receipt=args.attribution_receipt)
        print(json.dumps(applied, ensure_ascii=False, indent=2))
        return 0
    except (G6ConfigError, DecisionReceiptError, ValueError) as exc:
        print(f"G6 invocation/configuration error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
