from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from mosaik.exceptions import ScenarioError

ALLOWED_SIM_TYPES = {"time-based", "event-based", "hybrid"}
MODEL_SEQUENCE_FIELDS = (
    "params",
    "attrs",
    "trigger",
    "non-trigger",
    "persistent",
    "non-persistent",
)


def validate_meta(meta: Any, sim_id: str) -> None:
    """
    Validate the structure of a simulator's META definition and raise a
    :class:`ScenarioError` with a helpful message if the definition is
    inconsistent or malformed.
    """
    if not isinstance(meta, Mapping):
        raise ScenarioError(
            f"Simulator {sim_id} returned invalid META: expected a mapping, "
            f"got {type(meta).__name__}."
        )

    _ensure_key(meta, "api_version", sim_id)
    if "type" not in meta:
        raise ScenarioError(
            'The simulator is missing a type specification ("time-based", '
            '"event-based" or "hybrid"). This is required starting from API '
            "version 3."
        )
    _ensure_key(meta, "models", sim_id)

    _ensure_type(meta["api_version"], str, sim_id, "meta['api_version']")
    _ensure_sim_type(meta["type"], sim_id)
    models = meta["models"]
    if not isinstance(models, Mapping):
        raise ScenarioError(
            f"Simulator {sim_id} returned invalid META: meta['models'] must be a "
            f"mapping, got {type(models).__name__}."
        )

    extra_methods = meta.get("extra_methods")
    if extra_methods is not None:
        _ensure_sequence_of_strings(extra_methods, sim_id, "meta['extra_methods']")

    _validate_models(models, sim_id)


def _validate_models(models: Mapping[str, Any], sim_id: str) -> None:
    for model_name, description in models.items():
        if not isinstance(model_name, str):
            raise ScenarioError(
                f"Simulator {sim_id} returned invalid META: model names must be "
                f"strings, but found {type(model_name).__name__}."
            )
        path_prefix = f"meta['models']['{model_name}']"
        if not isinstance(description, Mapping):
            raise ScenarioError(
                f"Simulator {sim_id} returned invalid META: {path_prefix} must be a "
                f"mapping, got {type(description).__name__}."
            )

        public = description.get("public")
        if public is not None and not isinstance(public, bool):
            raise ScenarioError(
                f"Simulator {sim_id} returned invalid META: "
                f"{path_prefix}['public'] must be a boolean, "
                f"got {type(public).__name__}."
            )

        any_inputs = description.get("any_inputs")
        if any_inputs is not None and not isinstance(any_inputs, bool):
            raise ScenarioError(
                f"Simulator {sim_id} returned invalid META: "
                f"{path_prefix}['any_inputs'] must be a boolean, "
                f"got {type(any_inputs).__name__}."
            )

        for field in MODEL_SEQUENCE_FIELDS:
            if field in description:
                _ensure_sequence_of_strings(
                    description[field], sim_id, f"{path_prefix}['{field}']"
                )


def _ensure_key(meta: Mapping[str, Any], key: str, sim_id: str) -> None:
    if key not in meta:
        raise ScenarioError(
            f"Simulator {sim_id} returned invalid META: missing required key "
            f"'{key}'."
        )


def _ensure_type(value: Any, expected_type: type, sim_id: str, field_path: str) -> None:
    if not isinstance(value, expected_type):
        raise ScenarioError(
            f"Simulator {sim_id} returned invalid META: {field_path} must be a "
            f"{expected_type.__name__}, got {type(value).__name__}."
        )


def _ensure_sim_type(value: Any, sim_id: str) -> None:
    field_path = "meta['type']"
    if not isinstance(value, str):
        raise ScenarioError(
            f"Simulator {sim_id} returned invalid META: {field_path} must be a "
            f"string, got {type(value).__name__}."
        )
    if value not in ALLOWED_SIM_TYPES:
        raise ScenarioError(
            f"The type '{value}' is not a valid type. (It should be one of "
            "'time-based', 'event-based' and 'hybrid'.) Please check for typos "
            "in your simulator's init function and meta."
        )


def _ensure_sequence_of_strings(value: Any, sim_id: str, field_path: str) -> None:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise ScenarioError(
            f"Simulator {sim_id} returned invalid META: {field_path} must be a "
            "sequence of strings, "
            f"got {type(value).__name__}."
        )

    for idx, element in enumerate(value):
        if not isinstance(element, str):
            raise ScenarioError(
                f"Simulator {sim_id} returned invalid META: {field_path}[{idx}] must "
                f"be a string, got {type(element).__name__}."
            )
