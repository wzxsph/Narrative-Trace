#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from gamegen.save_contract import DEFAULT_SAVE_CONTRACT, validate_save_contract


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate local save contract fixtures.")
    parser.add_argument("--contract", default=str(DEFAULT_SAVE_CONTRACT), help="Save contract fixture JSON.")
    args = parser.parse_args()

    errors = validate_save_contract(args.contract)
    if errors:
        print("Save contract validation failed", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print("Save contract validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
