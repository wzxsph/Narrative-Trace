#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from gamegen.model_output_archive import DEFAULT_ARCHIVE_DIR, archive_model_output_sample
from gamegen.prompt_manifest import active_prompt_set_id


def main() -> int:
    parser = argparse.ArgumentParser(description="Archive a redacted model output sample with trace metadata.")
    parser.add_argument("--input", required=True, help="Raw model output text or JSON file to redact and archive.")
    parser.add_argument("--sample-id", required=True, help="Stable lowercase sample id, e.g. first_scene_polish_fail_001.")
    parser.add_argument("--provider", required=True, help="Model provider label, e.g. openai_compatible.")
    parser.add_argument("--model", required=True, help="Model id used for the sample.")
    parser.add_argument(
        "--prompt-set",
        default=None,
        help="Prompt set id declared in prompts/manifest.json. Defaults to the active prompt set.",
    )
    parser.add_argument("--source", required=True, help="Prompt or generation step that produced the sample.")
    parser.add_argument("--notes", default="", help="Short non-sensitive note about why the sample matters.")
    parser.add_argument("--out", default=str(DEFAULT_ARCHIVE_DIR), help="Archive directory.")
    parser.add_argument("--overwrite", action="store_true", help="Replace an existing sample with the same id.")
    args = parser.parse_args()

    try:
        entry = archive_model_output_sample(
            args.input,
            out_dir=args.out,
            sample_id=args.sample_id,
            provider=args.provider,
            model=args.model,
            prompt_set=args.prompt_set or active_prompt_set_id(),
            source=args.source,
            notes=args.notes,
            overwrite=args.overwrite,
        )
    except Exception as exc:  # noqa: BLE001 - CLI should report actionable failure
        print(f"Archive failed: {exc}", file=sys.stderr)
        return 1

    print("Archived model output sample")
    print(f"- id: {entry['id']}")
    print(f"- file: {Path(args.out) / entry['file']}")
    print(f"- provider/model: {entry['provider']} / {entry['model']}")
    print(f"- prompt_set: {entry['prompt_set']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
