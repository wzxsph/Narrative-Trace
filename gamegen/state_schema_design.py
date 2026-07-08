from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal


Level = Literal["error", "warning"]

REQUIRED_AXES = {"clues", "stance", "relationships", "pressure"}
REQUIRED_TOP_LEVEL_FIELDS = {
    "schema_version",
    "project_id",
    "axes",
    "variables",
    "relationship_axes",
    "ending_tags",
    "design_rules",
}
REQUIRED_VARIABLE_FIELDS = {"key", "axis", "type", "initial", "purpose", "written_by", "read_by"}
ALLOWED_VARIABLE_TYPES = {"boolean", "integer"}


@dataclass(frozen=True)
class StateSchemaDesignMessage:
    level: Level
    location: str
    message: str


def validate_state_schema_design(design: dict[str, Any]) -> list[StateSchemaDesignMessage]:
    messages: list[StateSchemaDesignMessage] = []

    for field in sorted(REQUIRED_TOP_LEVEL_FIELDS):
        if field not in design:
            messages.append(StateSchemaDesignMessage("error", field, "Missing required top-level field"))

    if design.get("schema_version") != "state_schema_design_v0_1":
        messages.append(
            StateSchemaDesignMessage(
                "error",
                "schema_version",
                "State schema design must use schema_version state_schema_design_v0_1",
            )
        )

    axes = design.get("axes")
    axis_ids: set[str] = set()
    if not isinstance(axes, list) or not axes:
        messages.append(StateSchemaDesignMessage("error", "axes", "Axes must be a non-empty list"))
    else:
        axis_ids = _collect_axis_ids(axes, messages)
        missing_axes = REQUIRED_AXES - axis_ids
        for axis_id in sorted(missing_axes):
            messages.append(StateSchemaDesignMessage("error", "axes", f"Missing required axis: {axis_id}"))

    variables = design.get("variables")
    variable_keys: set[str] = set()
    if not isinstance(variables, list) or not variables:
        messages.append(StateSchemaDesignMessage("error", "variables", "Variables must be a non-empty list"))
    else:
        variable_keys = _validate_variables(variables, axis_ids, messages)

    relationship_axes = design.get("relationship_axes")
    if not isinstance(relationship_axes, dict) or not relationship_axes:
        messages.append(
            StateSchemaDesignMessage("error", "relationship_axes", "Relationship axes must be a non-empty object")
        )
    else:
        _validate_relationship_axes(relationship_axes, variable_keys, messages)

    ending_tags = design.get("ending_tags")
    if not isinstance(ending_tags, list) or len(ending_tags) < 3:
        messages.append(StateSchemaDesignMessage("error", "ending_tags", "At least three ending tags are required"))

    design_rules = design.get("design_rules")
    if not isinstance(design_rules, list) or not design_rules:
        messages.append(StateSchemaDesignMessage("error", "design_rules", "Design rules must be a non-empty list"))

    return messages


def _collect_axis_ids(axes: list[Any], messages: list[StateSchemaDesignMessage]) -> set[str]:
    axis_ids: set[str] = set()
    for index, axis in enumerate(axes):
        location = f"axes[{index}]"
        if not isinstance(axis, dict):
            messages.append(StateSchemaDesignMessage("error", location, "Axis must be an object"))
            continue
        axis_id = axis.get("id")
        if not isinstance(axis_id, str) or not axis_id:
            messages.append(StateSchemaDesignMessage("error", f"{location}.id", "Axis id must be a non-empty string"))
            continue
        if axis_id in axis_ids:
            messages.append(StateSchemaDesignMessage("error", f"{location}.id", f"Duplicate axis id: {axis_id}"))
        axis_ids.add(axis_id)
        purpose = axis.get("purpose")
        if not isinstance(purpose, str) or len(purpose.strip()) < 8:
            messages.append(StateSchemaDesignMessage("warning", f"{location}.purpose", "Axis purpose is too thin"))
    return axis_ids


def _validate_variables(
    variables: list[Any],
    axis_ids: set[str],
    messages: list[StateSchemaDesignMessage],
) -> set[str]:
    variable_keys: set[str] = set()
    for index, variable in enumerate(variables):
        location = f"variables[{index}]"
        if not isinstance(variable, dict):
            messages.append(StateSchemaDesignMessage("error", location, "Variable must be an object"))
            continue

        for field in sorted(REQUIRED_VARIABLE_FIELDS):
            if field not in variable:
                messages.append(StateSchemaDesignMessage("error", f"{location}.{field}", "Missing variable field"))

        key = variable.get("key")
        axis = variable.get("axis")
        value_type = variable.get("type")

        if not isinstance(key, str) or not key:
            messages.append(StateSchemaDesignMessage("error", f"{location}.key", "Variable key must be a string"))
        elif key in variable_keys:
            messages.append(StateSchemaDesignMessage("error", f"{location}.key", f"Duplicate variable key: {key}"))
        elif key.startswith("relationships.") and axis != "relationships":
            messages.append(
                StateSchemaDesignMessage(
                    "error",
                    f"{location}.axis",
                    "Relationship variable keys must use relationships axis",
                )
            )
        if isinstance(key, str) and key:
            variable_keys.add(key)

        if not isinstance(axis, str) or not axis:
            messages.append(StateSchemaDesignMessage("error", f"{location}.axis", "Variable axis must be a string"))
        elif axis_ids and axis not in axis_ids:
            messages.append(StateSchemaDesignMessage("error", f"{location}.axis", f"Unknown variable axis: {axis}"))

        if value_type not in ALLOWED_VARIABLE_TYPES:
            messages.append(
                StateSchemaDesignMessage(
                    "error",
                    f"{location}.type",
                    "Variable type must be one of: boolean, integer",
                )
            )

        purpose = variable.get("purpose")
        if not isinstance(purpose, str) or len(purpose.strip()) < 8:
            messages.append(StateSchemaDesignMessage("warning", f"{location}.purpose", "Variable purpose is too thin"))

        for list_field in ("written_by", "read_by"):
            refs = variable.get(list_field)
            if not isinstance(refs, list) or not refs or not all(isinstance(ref, str) and ref for ref in refs):
                messages.append(
                    StateSchemaDesignMessage(
                        "error",
                        f"{location}.{list_field}",
                        f"{list_field} must be a non-empty list of ids",
                    )
                )
    return variable_keys


def _validate_relationship_axes(
    relationship_axes: dict[Any, Any],
    variable_keys: set[str],
    messages: list[StateSchemaDesignMessage],
) -> None:
    for character_id, axes in relationship_axes.items():
        location = f"relationship_axes.{character_id}"
        if not isinstance(character_id, str) or not character_id:
            messages.append(StateSchemaDesignMessage("error", "relationship_axes", "Character id must be a string"))
            continue
        if not isinstance(axes, list) or not axes:
            messages.append(StateSchemaDesignMessage("error", location, "Character relationship axes must be a list"))
            continue
        seen_axes: set[str] = set()
        for axis_name in axes:
            if not isinstance(axis_name, str) or not axis_name:
                messages.append(StateSchemaDesignMessage("error", location, "Relationship axis name must be a string"))
                continue
            if axis_name in seen_axes:
                messages.append(StateSchemaDesignMessage("error", location, f"Duplicate relationship axis: {axis_name}"))
            seen_axes.add(axis_name)
            expected_key = f"relationships.{character_id}.{axis_name}"
            if expected_key not in variable_keys:
                messages.append(
                    StateSchemaDesignMessage(
                        "error",
                        location,
                        f"Declared relationship axis has no variable: {expected_key}",
                    )
                )
