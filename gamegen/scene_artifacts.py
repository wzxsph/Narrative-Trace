from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Literal

from .blueprint_alignment import collect_observe_ids, collect_state_writes
from .demo_agent import deterministic_demo_game


Level = Literal["error", "warning"]
ALLOWED_ARTIFACT_STATUSES = {"draft", "locked", "rejected"}


@dataclass(frozen=True)
class SceneArtifactMessage:
    level: Level
    location: str
    message: str


def build_scene_artifacts_from_library(brief: dict[str, Any], scene_blueprint: dict[str, Any]) -> dict[str, Any]:
    game = deterministic_demo_game(brief)
    scene_by_id = {scene["id"]: scene for scene in game["scenes"]}
    artifacts: list[dict[str, Any]] = []
    missing_scene_ids: list[str] = []

    for blueprint_scene in scene_blueprint.get("scenes", []):
        scene_id = blueprint_scene.get("id")
        scene = scene_by_id.get(scene_id)
        if scene is None:
            missing_scene_ids.append(str(scene_id))
            continue
        artifacts.append(
            {
                "scene_id": scene_id,
                "blueprint_scene_role": blueprint_scene.get("scene_role"),
                "source": "demo_scene_library_v0_1",
                "status": "draft",
                "review": {
                    "state": "unreviewed",
                    "reviewer": None,
                    "notes": [],
                },
                "scene": deepcopy(scene),
            }
        )

    if missing_scene_ids:
        raise ValueError(f"Scene blueprint references missing demo scenes: {', '.join(missing_scene_ids)}")

    return {
        "schema_version": "scene_artifacts_v0_1",
        "project_id": brief["project"]["id"],
        "source_scene_blueprint_version": scene_blueprint["schema_version"],
        "entry_scene_id": scene_blueprint["entry_scene_id"],
        "artifacts": artifacts,
    }


def validate_scene_artifacts(
    scene_artifacts: dict[str, Any],
    scene_blueprint: dict[str, Any],
) -> list[SceneArtifactMessage]:
    messages: list[SceneArtifactMessage] = []
    if scene_artifacts.get("schema_version") != "scene_artifacts_v0_1":
        messages.append(SceneArtifactMessage("error", "schema_version", "Scene artifacts must use scene_artifacts_v0_1"))

    if scene_artifacts.get("entry_scene_id") != scene_blueprint.get("entry_scene_id"):
        messages.append(SceneArtifactMessage("error", "entry_scene_id", "Scene artifacts entry must match blueprint entry"))

    artifacts = scene_artifacts.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        messages.append(SceneArtifactMessage("error", "artifacts", "Artifacts must be a non-empty list"))
        return messages

    blueprint_scenes = scene_blueprint.get("scenes", [])
    blueprint_ids = [scene.get("id") for scene in blueprint_scenes if isinstance(scene, dict)]
    artifact_ids = [artifact.get("scene_id") for artifact in artifacts if isinstance(artifact, dict)]
    if artifact_ids != blueprint_ids:
        messages.append(SceneArtifactMessage("error", "artifacts", "Artifact scene order must match blueprint scene order"))

    seen_ids: set[str] = set()
    blueprint_by_id = {scene.get("id"): scene for scene in blueprint_scenes if isinstance(scene, dict)}
    for index, artifact in enumerate(artifacts):
        location = f"artifacts[{index}]"
        if not isinstance(artifact, dict):
            messages.append(SceneArtifactMessage("error", location, "Artifact must be an object"))
            continue
        scene_id = artifact.get("scene_id")
        if not isinstance(scene_id, str) or not scene_id:
            messages.append(SceneArtifactMessage("error", f"{location}.scene_id", "Artifact scene_id must be a string"))
            continue
        if scene_id in seen_ids:
            messages.append(SceneArtifactMessage("error", f"{location}.scene_id", f"Duplicate artifact scene_id: {scene_id}"))
        seen_ids.add(scene_id)

        status = artifact.get("status")
        if status not in ALLOWED_ARTIFACT_STATUSES:
            messages.append(SceneArtifactMessage("error", f"{location}.status", "Artifact status must be draft, locked, or rejected"))

        review = artifact.get("review")
        if not isinstance(review, dict):
            messages.append(SceneArtifactMessage("error", f"{location}.review", "Artifact review must be an object"))
        else:
            notes = review.get("notes")
            if not isinstance(notes, list) or not all(isinstance(note, str) for note in notes):
                messages.append(SceneArtifactMessage("error", f"{location}.review.notes", "Review notes must be a list of strings"))

        scene = artifact.get("scene")
        if not isinstance(scene, dict):
            messages.append(SceneArtifactMessage("error", f"{location}.scene", "Artifact scene must be an object"))
            continue
        if scene.get("id") != scene_id:
            messages.append(SceneArtifactMessage("error", f"{location}.scene.id", "Artifact scene id must match scene_id"))

        blueprint_scene = blueprint_by_id.get(scene_id)
        if blueprint_scene is None:
            messages.append(SceneArtifactMessage("error", f"{location}.scene_id", f"Artifact scene is not in blueprint: {scene_id}"))
            continue

        observe_ids = collect_observe_ids(scene)
        choice_ids = {choice.get("id") for choice in scene.get("choices", []) if isinstance(choice, dict)}
        state_writes = collect_state_writes(scene)
        for observe_id in blueprint_scene.get("observe_targets", []):
            if observe_id not in observe_ids:
                messages.append(
                    SceneArtifactMessage(
                        "error",
                        f"{location}.scene",
                        f"Scene artifact is missing planned observe: {observe_id}",
                    )
                )
        for choice_id in blueprint_scene.get("choice_targets", []):
            if choice_id not in choice_ids:
                messages.append(
                    SceneArtifactMessage(
                        "error",
                        f"{location}.scene",
                        f"Scene artifact is missing planned choice: {choice_id}",
                    )
                )
        for state_key in blueprint_scene.get("state_writes", []):
            if state_key not in state_writes:
                messages.append(
                    SceneArtifactMessage(
                        "error",
                        f"{location}.scene",
                        f"Scene artifact does not write planned state: {state_key}",
                    )
                )

    return messages


def review_scene_artifacts(scene_artifacts: dict[str, Any], reviewer: str = "deterministic_reviewer_v0_1") -> dict[str, Any]:
    reviewed = deepcopy(scene_artifacts)
    reviewed["review_schema_version"] = "scene_artifact_review_v0_1"
    for artifact in reviewed.get("artifacts", []):
        if not isinstance(artifact, dict):
            continue
        artifact["status"] = "locked"
        artifact["review"] = {
            "state": "approved",
            "reviewer": reviewer,
            "notes": [
                "Structure gates passed before deterministic release.",
                "Scene artifact is locked for compile.",
            ],
        }
    return reviewed


def validate_scene_artifact_release(scene_artifacts: dict[str, Any]) -> list[SceneArtifactMessage]:
    messages: list[SceneArtifactMessage] = []
    if scene_artifacts.get("review_schema_version") != "scene_artifact_review_v0_1":
        messages.append(
            SceneArtifactMessage("error", "review_schema_version", "Scene artifacts must include review schema before release")
        )
    artifacts = scene_artifacts.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        messages.append(SceneArtifactMessage("error", "artifacts", "Artifacts must be a non-empty list"))
        return messages
    for index, artifact in enumerate(artifacts):
        location = f"artifacts[{index}]"
        if not isinstance(artifact, dict):
            messages.append(SceneArtifactMessage("error", location, "Artifact must be an object"))
            continue
        if artifact.get("status") != "locked":
            messages.append(SceneArtifactMessage("error", f"{location}.status", "Artifact must be locked before compile"))
        review = artifact.get("review")
        if not isinstance(review, dict):
            messages.append(SceneArtifactMessage("error", f"{location}.review", "Artifact review must be an object"))
            continue
        if review.get("state") != "approved":
            messages.append(SceneArtifactMessage("error", f"{location}.review.state", "Artifact review must be approved"))
        if not isinstance(review.get("reviewer"), str) or not review.get("reviewer"):
            messages.append(SceneArtifactMessage("error", f"{location}.review.reviewer", "Artifact reviewer is required"))
    return messages


def compile_game_from_scene_artifacts(brief: dict[str, Any], scene_artifacts: dict[str, Any]) -> dict[str, Any]:
    release_messages = validate_scene_artifact_release(scene_artifacts)
    release_errors = [message for message in release_messages if message.level == "error"]
    if release_errors:
        raise ValueError("Scene artifacts must be locked before compile")
    game = deterministic_demo_game(brief)
    scenes = [deepcopy(artifact["scene"]) for artifact in scene_artifacts.get("artifacts", [])]
    game["start_scene_id"] = scene_artifacts.get("entry_scene_id", game["start_scene_id"])
    game["scenes"] = scenes
    generation = game.setdefault("generation", {})
    generation["draft_source"] = "scene_artifacts_v0_1"
    generation["compiled_scene_count"] = len(scenes)
    return game
