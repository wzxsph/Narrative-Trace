#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from gamegen.model_output_archive import DEFAULT_ARCHIVE_DIR, validate_model_output_archive


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate redacted model output sample archive.")
    parser.add_argument("--archive", default=str(DEFAULT_ARCHIVE_DIR), help="Model output sample archive directory.")
    args = parser.parse_args()

    errors = validate_model_output_archive(args.archive)
    if errors:
        print("Model output archive validation failed", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print("Model output archive validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
