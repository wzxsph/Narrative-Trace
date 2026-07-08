from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .prompt_manifest import DEFAULT_MANIFEST, declared_prompt_set_ids


DEFAULT_ARCHIVE_DIR = Path(__file__).resolve().parents[1] / "examples" / "fixtures" / "model_outputs"
SAMPLE_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{2,80}$")

REDACTION_RULES: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"sk-[A-Za-z0-9_-]{8,}"), "sk-[REDACTED]"),
    (re.compile(r"Bearer\s+[A-Za-z0-9._~+/=-]{8,}", re.IGNORECASE), "Bearer REDACTED"),
    (
        re.compile(r'("(?:api[_-]?key|authorization|token)"\s*:\s*")[^"]+(")', re.IGNORECASE),
        r"\1REDACTED\2",
    ),
    (
        re.compile(r"\b((?:LLM_API_KEY|OPENAI_API_KEY|API_KEY|TOKEN)\s*=\s*)[^\s]+", re.IGNORECASE),
        r"\1REDACTED",
    ),
    (
        re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE),
        "[REDACTED_EMAIL]",
    ),
)

SECRET_DETECTORS: tuple[re.Pattern[str], ...] = (
    re.compile(r"sk-(?!\[REDACTED\])[A-Za-z0-9_-]{8,}"),
    re.compile(r"Bearer\s+(?!REDACTED\b)[A-Za-z0-9._~+/=-]{8,}", re.IGNORECASE),
    re.compile(r'("(?:api[_-]?key|authorization|token)"\s*:\s*")(?!REDACTED")[^"]+(")', re.IGNORECASE),
    re.compile(r"\b(?:LLM_API_KEY|OPENAI_API_KEY|API_KEY|TOKEN)\s*=\s*(?!REDACTED\b)[^\s]+", re.IGNORECASE),
    re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE),
)


def redact_sample_text(text: str) -> str:
    redacted = text
    for pattern, replacement in REDACTION_RULES:
        redacted = pattern.sub(replacement, redacted)
    return redacted


def assert_no_unredacted_secrets(text: str) -> None:
    for detector in SECRET_DETECTORS:
        if detector.search(text):
            raise ValueError(f"Redaction failed for pattern: {detector.pattern}")


def archive_model_output_sample(
    input_path: str | Path,
    *,
    out_dir: str | Path = DEFAULT_ARCHIVE_DIR,
    sample_id: str,
    provider: str,
    model: str,
    prompt_set: str,
    source: str,
    notes: str = "",
    created_at: str | None = None,
    prompt_manifest: str | Path = DEFAULT_MANIFEST,
    overwrite: bool = False,
) -> dict[str, Any]:
    if not SAMPLE_ID_RE.match(sample_id):
        raise ValueError("sample_id must use lowercase letters, numbers, '-' or '_' and be 3-80 chars")
    if not provider.strip():
        raise ValueError("provider is required")
    if not model.strip():
        raise ValueError("model is required")
    if not source.strip():
        raise ValueError("source is required")

    declared_ids = declared_prompt_set_ids(prompt_manifest)
    if prompt_set not in declared_ids:
        raise ValueError(f"prompt_set '{prompt_set}' is not declared in prompt manifest")

    raw_text = Path(input_path).read_text(encoding="utf-8")
    redacted_text = redact_sample_text(raw_text)
    assert_no_unredacted_secrets(redacted_text)
    if not redacted_text.endswith("\n"):
        redacted_text += "\n"

    archive_dir = Path(out_dir)
    samples_dir = archive_dir / "samples"
    samples_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = archive_dir / "sample_manifest.json"
    manifest = load_sample_manifest(manifest_path)

    sample_path = samples_dir / f"{sample_id}.txt"
    if sample_path.exists() and not overwrite:
        raise ValueError(f"Sample already exists: {sample_path}")

    entry = {
        "id": sample_id,
        "file": str(sample_path.relative_to(archive_dir)),
        "provider": provider,
        "model": model,
        "prompt_set": prompt_set,
        "source": source,
        "schema": "schemas/game.schema.json",
        "created_at": created_at or utc_now_iso(),
        "sha256": hashlib.sha256(redacted_text.encode("utf-8")).hexdigest(),
        "redaction": "api_keys,bearer_tokens,auth_fields,env_tokens,emails",
        "notes": notes,
    }

    sample_path.write_text(redacted_text, encoding="utf-8")
    upsert_manifest_entry(manifest, entry, overwrite=overwrite)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return entry


def validate_model_output_archive(
    archive_dir: str | Path = DEFAULT_ARCHIVE_DIR,
    *,
    prompt_manifest: str | Path = DEFAULT_MANIFEST,
) -> list[str]:
    errors: list[str] = []
    archive_path = Path(archive_dir)
    manifest_path = archive_path / "sample_manifest.json"
    if not manifest_path.exists():
        return [f"Missing sample manifest: {manifest_path}"]

    try:
        manifest = load_sample_manifest(manifest_path)
    except Exception as exc:  # noqa: BLE001 - return all validation issues as strings
        return [f"Invalid sample manifest: {exc}"]

    if manifest.get("schema_version") != "game_writer_model_output_samples_v0_1":
        errors.append("sample_manifest.json has unsupported schema_version")

    declared_ids = declared_prompt_set_ids(prompt_manifest)
    seen_ids: set[str] = set()
    for index, entry in enumerate(manifest.get("samples", [])):
        location = f"samples[{index}]"
        if not isinstance(entry, dict):
            errors.append(f"{location}: entry must be an object")
            continue

        sample_id = entry.get("id")
        if not isinstance(sample_id, str) or not SAMPLE_ID_RE.match(sample_id):
            errors.append(f"{location}: invalid sample id")
        elif sample_id in seen_ids:
            errors.append(f"{location}: duplicate sample id '{sample_id}'")
        else:
            seen_ids.add(sample_id)

        for field in ("provider", "model", "prompt_set", "source", "schema", "sha256"):
            if not isinstance(entry.get(field), str) or not entry[field].strip():
                errors.append(f"{location}: missing {field}")

        prompt_set = entry.get("prompt_set")
        if isinstance(prompt_set, str) and prompt_set and prompt_set not in declared_ids:
            errors.append(f"{location}: prompt_set '{prompt_set}' is not declared")

        if entry.get("schema") != "schemas/game.schema.json":
            errors.append(f"{location}: schema must be schemas/game.schema.json")

        sample_file = entry.get("file")
        if not isinstance(sample_file, str) or not sample_file:
            errors.append(f"{location}: missing file")
            continue
        relative_file = Path(sample_file)
        if relative_file.is_absolute() or ".." in relative_file.parts:
            errors.append(f"{location}: file must be a relative path inside archive")
            continue

        sample_path = archive_path / relative_file
        if not sample_path.exists():
            errors.append(f"{location}: sample file missing: {sample_file}")
            continue

        text = sample_path.read_text(encoding="utf-8")
        try:
            assert_no_unredacted_secrets(text)
        except ValueError as exc:
            errors.append(f"{location}: sample still contains unredacted secret: {exc}")

        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        if isinstance(entry.get("sha256"), str) and entry["sha256"] != digest:
            errors.append(f"{location}: sha256 mismatch")

    return errors


def load_sample_manifest(path: str | Path) -> dict[str, Any]:
    manifest_path = Path(path)
    if not manifest_path.exists():
        return {
            "schema_version": "game_writer_model_output_samples_v0_1",
            "description": "Redacted model output samples with provider/model/prompt metadata.",
            "samples": [],
        }
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest.get("samples"), list):
        raise ValueError("sample_manifest.json must contain a samples array")
    return manifest


def upsert_manifest_entry(manifest: dict[str, Any], entry: dict[str, Any], *, overwrite: bool) -> None:
    samples = manifest.setdefault("samples", [])
    for index, existing in enumerate(samples):
        if isinstance(existing, dict) and existing.get("id") == entry["id"]:
            if not overwrite:
                raise ValueError(f"Manifest already contains sample id: {entry['id']}")
            samples[index] = entry
            break
    else:
        samples.append(entry)
    samples.sort(key=lambda item: item.get("id", "") if isinstance(item, dict) else "")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
