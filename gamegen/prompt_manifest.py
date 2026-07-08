from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "prompts" / "manifest.json"


def load_prompt_manifest(path: str | Path = DEFAULT_MANIFEST) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def active_prompt_set_id(path: str | Path = DEFAULT_MANIFEST) -> str:
    manifest = load_prompt_manifest(path)
    prompt_set_id = manifest.get("active_prompt_set")
    if not isinstance(prompt_set_id, str) or not prompt_set_id:
        raise ValueError("Prompt manifest missing active_prompt_set")
    prompt_sets = manifest.get("prompt_sets", [])
    if not any(item.get("id") == prompt_set_id for item in prompt_sets if isinstance(item, dict)):
        raise ValueError(f"Prompt manifest active_prompt_set '{prompt_set_id}' is not declared")
    return prompt_set_id
