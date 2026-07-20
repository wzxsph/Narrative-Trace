#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from gamegen.gates import GATE_IDS, run_pack_gates
from gamegen.g5 import run_g5


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Framework V1 content-pack gates.")
    parser.add_argument("pack_dir", help="Directory containing pack.json")
    parser.add_argument("--through", choices=GATE_IDS[:5], default="G4")
    parser.add_argument("--json-out", help="Optional path for the machine-readable gate report")
    args = parser.parse_args(argv)
    try:
        results = run_pack_gates(args.pack_dir, through=args.through, g5_runner=run_g5)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    report = {"schema_version": "narrative_gate_chain_report_v1", "results": [item.to_dict() for item in results]}
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    if args.json_out:
        output = Path(args.json_out)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    if any(item.status == "failed" for item in results):
        return 1
    if any(item.status == "pending" for item in results):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
