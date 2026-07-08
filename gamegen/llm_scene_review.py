from __future__ import annotations

import json
from typing import Any

from .llm_client import LLMClient


ALLOWED_VERDICTS = {"pass", "revise"}
ALLOWED_RISK_FLAGS = {
    "missing_observe_payoff",
    "weak_choice_consequence",
    "unfair_hidden_information",
    "state_echo_missing",
    "tone_drift",
    "none",
}


def review_scene_artifact_with_llm(
    scene_artifacts: dict[str, Any],
    scene_blueprint: dict[str, Any],
    client: LLMClient,
    scene_id: str | None = None,
) -> dict[str, Any]:
    artifact = select_scene_artifact(scene_artifacts, scene_id)
    blueprint_scene = select_blueprint_scene(scene_blueprint, artifact["scene_id"])
    system_prompt = (
        "You are a conservative QA reviewer for a vertical mobile text adventure. "
        "Return JSON only. Do not rewrite the scene. Do not add new IDs."
    )
    user_prompt = json.dumps(
        {
            "task": "Review whether the scene artifact satisfies its blueprint and is safe to keep locked.",
            "return_shape": {
                "scene_id": artifact["scene_id"],
                "verdict": "pass|revise",
                "risk_flags": ["one or more allowed flags"],
                "notes": ["short Chinese notes, max 3"],
            },
            "allowed_risk_flags": sorted(ALLOWED_RISK_FLAGS),
            "blueprint_scene": blueprint_scene,
            "scene_summary": {
                "id": artifact["scene"]["id"],
                "title": artifact["scene"]["title"],
                "task": artifact["scene"]["task"],
                "pressure": artifact["scene"]["pressure"],
                "observe_anchor_ids": [
                    anchor["id"]
                    for block in artifact["scene"].get("background_blocks", [])
                    for anchor in block.get("observe_anchors", [])
                ],
                "choice_ids": [choice["id"] for choice in artifact["scene"].get("choices", [])],
            },
        },
        ensure_ascii=False,
    )
    result = client.complete_json(system_prompt, user_prompt)
    return normalize_llm_scene_review(result, artifact["scene_id"])


def normalize_llm_scene_review(result: dict[str, Any], expected_scene_id: str) -> dict[str, Any]:
    scene_id = result.get("scene_id")
    verdict = result.get("verdict")
    risk_flags = result.get("risk_flags")
    notes = result.get("notes")

    if scene_id != expected_scene_id:
        raise RuntimeError(f"LLM scene review returned wrong scene_id: {scene_id}")
    if verdict not in ALLOWED_VERDICTS:
        raise RuntimeError(f"LLM scene review returned invalid verdict: {verdict}")
    if not isinstance(risk_flags, list) or not risk_flags:
        raise RuntimeError("LLM scene review risk_flags must be a non-empty list")
    normalized_flags = []
    for flag in risk_flags:
        if flag not in ALLOWED_RISK_FLAGS:
            raise RuntimeError(f"LLM scene review returned invalid risk flag: {flag}")
        normalized_flags.append(flag)
    if not isinstance(notes, list) or not all(isinstance(note, str) and note for note in notes):
        raise RuntimeError("LLM scene review notes must be a non-empty list of strings")

    return {
        "schema_version": "llm_scene_review_v0_1",
        "scene_id": scene_id,
        "verdict": verdict,
        "risk_flags": normalized_flags,
        "notes": notes[:3],
    }


def select_scene_artifact(scene_artifacts: dict[str, Any], scene_id: str | None = None) -> dict[str, Any]:
    artifacts = scene_artifacts.get("artifacts", [])
    if not artifacts:
        raise RuntimeError("No scene artifacts available for LLM review")
    if scene_id is None:
        return artifacts[0]
    for artifact in artifacts:
        if artifact.get("scene_id") == scene_id:
            return artifact
    raise RuntimeError(f"Scene artifact not found for LLM review: {scene_id}")


def select_blueprint_scene(scene_blueprint: dict[str, Any], scene_id: str) -> dict[str, Any]:
    for scene in scene_blueprint.get("scenes", []):
        if scene.get("id") == scene_id:
            return scene
    raise RuntimeError(f"Blueprint scene not found for LLM review: {scene_id}")
