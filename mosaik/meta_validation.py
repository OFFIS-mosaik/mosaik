from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any, Dict, FrozenSet, Tuple

from typing_extensions import Literal

from mosaik.exceptions import ScenarioError
from mosaik.in_or_out_set import InOrOutSet, OutSet, parse_set_triple, wrap_set
from mosaik_api_v3.types import Attr, Meta, ModelDescription, ModelName

ALLOWED_SIM_TYPES = {"time-based", "event-based", "hybrid"}
META_FIELDS = {"api_version", "type", "models", "extra_methods", "set_events"}
MODEL_FIELDS = {
    "public",
    "params",
    "attrs",
    "trigger",
    "non-trigger",
    "persistent",
    "non-persistent",
    "any_inputs",
}


@dataclass(frozen=True)
class ParsedModel:
    name: ModelName
    public: bool
    params: Tuple[str, ...]
    any_inputs: bool
    attrs: Tuple[str, ...] | None
    trigger: Tuple[str, ...] | None
    non_trigger: Tuple[str, ...] | None
    persistent: Tuple[str, ...] | None
    non_persistent: Tuple[str, ...] | None
    measurement_inputs: InOrOutSet[Attr]
    event_inputs: InOrOutSet[Attr]
    measurement_outputs: InOrOutSet[Attr]
    event_outputs: InOrOutSet[Attr]
    extras: Dict[str, Any]

    def to_meta_fragment(self) -> ModelDescription:
        model: Dict[str, Any] = dict(self.extras)
        model["public"] = self.public
        model["params"] = list(self.params)
        if self.attrs is not None:
            model["attrs"] = list(self.attrs)
        if self.trigger is not None:
            model["trigger"] = list(self.trigger)
        if self.non_trigger is not None:
            model["non-trigger"] = list(self.non_trigger)
        if self.persistent is not None:
            model["persistent"] = list(self.persistent)
        if self.non_persistent is not None:
            model["non-persistent"] = list(self.non_persistent)
        if self.any_inputs:
            model["any_inputs"] = self.any_inputs
        return model  # type: ignore[return-value]


@dataclass(frozen=True)
class ParsedMeta:
    api_version: str
    sim_type: Literal["time-based", "event-based", "hybrid"]
    models: Dict[ModelName, ParsedModel]
    extra_methods: Tuple[str, ...]
    set_events: bool
    extras: Dict[str, Any]

    def to_meta(self) -> Meta:
        models: Dict[str, ModelDescription] = {
            name: model.to_meta_fragment() for name, model in self.models.items()
        }
        meta: Dict[str, Any] = {
            "api_version": self.api_version,
            "type": self.sim_type,
            "models": models,
        }
        if self.extra_methods:
            meta["extra_methods"] = list(self.extra_methods)
        if self.set_events:
            meta["set_events"] = self.set_events
        meta.update(self.extras)
        return meta  # type: ignore[return-value]


def parse_attrs(
    model_desc: ModelDescription, type: Literal["time-based", "event-based", "hybrid"]
) -> Tuple[InOrOutSet[Attr], InOrOutSet[Attr], InOrOutSet[Attr], InOrOutSet[Attr]]:
    """Parse the attrs and their trigger/persistent state.

    The guiding principle is this: The user can specify as little
    information as possible and the rest will be inferred, but
    inconsistent information will lead to an error.

    If attrs, trigger and non-trigger are all given, trigger and
    non-trigger must form a partition of attrs. If only two are given,
    the third in inferred, provided this can be done in such a way that
    trigger and non-trigger form a partition of attrs. If
    any_inputs=True, the set of all possible attrs is used instead of
    the ones specified in attrs. If only attrs is given, a default
    is chosen for the others, based on the type of the simulator.

    The same applieds to attrs, persistent and non-persistent, except
    that any_inputs is not considered (as these are outputs).

    :param model_desc: The `ModelDescription` to parse
    :param type: The simulator's type (for setting default attribute
        types).
    :return: A four-tuple of :class:`InOrOutSet`, giving the
        measurement inputs, event inputs, measurement outputs, and event
        outputs.
    :raises ValueError: if the information is insufficient or
        inconsistent
    """
    error_template = (
        "%s simulators may not specify %s attrs (use a hybrid simulator, instead, "
        "if you need both types of %s attributes), and they must list all their "
        "attrs as %s if that key is present"
    )

    if model_desc.get("any_inputs", False):
        inputs: InOrOutSet[Attr] | None = OutSet()
    else:
        inputs = wrap_set(model_desc.get("attrs"))
    empty: FrozenSet[Attr] = frozenset()
    if type == "time-based":
        default_measurements = None
        default_events = empty
    elif type == "event-based":
        default_measurements = empty
        default_events = None
    elif type == "hybrid":
        default_measurements = None if "trigger" in model_desc else inputs
        default_events = None
    measurement_inputs = wrap_set(model_desc.get("non-trigger", default_measurements))
    event_inputs = wrap_set(model_desc.get("trigger", default_events))
    measurement_inputs, event_inputs = parse_set_triple(
        inputs, measurement_inputs, event_inputs, "attrs", "non-trigger", "trigger"
    )
    if type == "time-based" and event_inputs != frozenset():
        raise ValueError(
            error_template % ("time-based", "trigger", "input", "non-trigger")
        )
    if type == "event-based" and measurement_inputs != frozenset():
        raise ValueError(
            error_template % ("event-based", "non-trigger", "inpus", "trigger")
        )

    outputs = wrap_set(model_desc.get("attrs"))
    default_measurements = empty if type == "event-based" else None
    measurement_outputs = wrap_set(model_desc.get("persistent", default_measurements))
    default_events = None if type == "event-based" else empty
    event_outputs = wrap_set(model_desc.get("non-persistent", default_events))
    measurement_outputs, event_outputs = parse_set_triple(
        outputs,
        measurement_outputs,
        event_outputs,
        "attrs",
        "persistent",
        "non-persistent",
    )
    if type == "time-based" and event_outputs != frozenset():
        raise ValueError(
            error_template % ("time-based", "non-persistent", "output", "persistent")
        )
    if type == "event-based" and measurement_outputs != frozenset():
        raise ValueError(
            error_template % ("event-based", "persistent", "output", "non-persistent")
        )

    return measurement_inputs, event_inputs, measurement_outputs, event_outputs


def validate_meta(meta: Any, sim_id: str) -> ParsedMeta:
    """
    Validate the structure of a simulator's META definition and raise a
    :class:`ScenarioError` with a helpful message if the definition is
    inconsistent or malformed.
    """
    return parse_meta(meta, sim_id)


def parse_meta(meta: Any, sim_id: str) -> ParsedMeta:
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

    extra_methods = _coerce_iterable_of_strings(
        meta.get("extra_methods"), sim_id, "meta['extra_methods']", allow_none=True
    )
    if extra_methods is None:
        extra_methods = ()

    set_events = meta.get("set_events", False)
    if not isinstance(set_events, bool):
        raise ScenarioError(
            f"Simulator {sim_id} returned invalid META: meta['set_events'] must be a "
            f"boolean, got {type(set_events).__name__}."
        )

    parsed_models = {
        model_name: _parse_model(model_name, description, sim_id, meta["type"])
        for model_name, description in models.items()
    }

    extras = {key: value for key, value in meta.items() if key not in META_FIELDS}
    return ParsedMeta(
        api_version=meta["api_version"],
        sim_type=meta["type"],
        models=parsed_models,
        extra_methods=tuple(extra_methods),
        set_events=set_events,
        extras=extras,
    )


def _parse_model(
    model_name: Any,
    description: Any,
    sim_id: str,
    sim_type: Literal["time-based", "event-based", "hybrid"],
) -> ParsedModel:
    if not isinstance(model_name, str):
        raise ScenarioError(
            f"Simulator {sim_id} returned invalid META: model names must be strings, "
            f"but found {type(model_name).__name__}."
        )
    path_prefix = f"meta['models']['{model_name}']"
    if not isinstance(description, Mapping):
        raise ScenarioError(
            f"Simulator {sim_id} returned invalid META: {path_prefix} must be a "
            f"mapping, got {type(description).__name__}."
        )

    public = description.get("public", True)
    if not isinstance(public, bool):
        raise ScenarioError(
            f"Simulator {sim_id} returned invalid META: "
            f"{path_prefix}['public'] must be a boolean, "
            f"got {type(public).__name__}."
        )

    any_inputs = description.get("any_inputs", False)
    if not isinstance(any_inputs, bool):
        raise ScenarioError(
            f"Simulator {sim_id} returned invalid META: "
            f"{path_prefix}['any_inputs'] must be a boolean, "
            f"got {type(any_inputs).__name__}."
        )

    params = _coerce_iterable_of_strings(
        description.get("params", ()), sim_id, f"{path_prefix}['params']"
    )
    attrs = _coerce_iterable_of_strings(
        description.get("attrs"), sim_id, f"{path_prefix}['attrs']", allow_none=True
    )
    trigger = _coerce_iterable_of_strings(
        description.get("trigger"), sim_id, f"{path_prefix}['trigger']",
        allow_none=True,
    )
    non_trigger = _coerce_iterable_of_strings(
        description.get("non-trigger"),
        sim_id,
        f"{path_prefix}['non-trigger']",
        allow_none=True,
    )
    persistent = _coerce_iterable_of_strings(
        description.get("persistent"),
        sim_id,
        f"{path_prefix}['persistent']",
        allow_none=True,
    )
    non_persistent = _coerce_iterable_of_strings(
        description.get("non-persistent"),
        sim_id,
        f"{path_prefix}['non-persistent']",
        allow_none=True,
    )

    extras = {key: value for key, value in description.items() if key not in MODEL_FIELDS}

    model_for_attrs: ModelDescription = {
        "params": [],
        "public": public,
    }
    if attrs is not None:
        model_for_attrs["attrs"] = attrs  # type: ignore[assignment]
    if trigger is not None:
        model_for_attrs["trigger"] = trigger  # type: ignore[assignment]
    if non_trigger is not None:
        model_for_attrs["non-trigger"] = non_trigger  # type: ignore[assignment]
    if persistent is not None:
        model_for_attrs["persistent"] = persistent  # type: ignore[assignment]
    if non_persistent is not None:
        model_for_attrs["non-persistent"] = non_persistent  # type: ignore[assignment]
    if any_inputs:
        model_for_attrs["any_inputs"] = any_inputs  # type: ignore[assignment]

    try:
        (
            measurement_inputs,
            event_inputs,
            measurement_outputs,
            event_outputs,
        ) = parse_attrs(model_for_attrs, sim_type)
    except ValueError as err:
        raise ValueError(
            f"while parsing the model description of model {model_name} of the "
            f"simulator {sim_id}: {err}"
        )

    return ParsedModel(
        name=model_name,
        public=public,
        params=tuple(params),
        any_inputs=any_inputs,
        attrs=attrs,
        trigger=trigger,
        non_trigger=non_trigger,
        persistent=persistent,
        non_persistent=non_persistent,
        measurement_inputs=measurement_inputs,
        event_inputs=event_inputs,
        measurement_outputs=measurement_outputs,
        event_outputs=event_outputs,
        extras=extras,
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


def _coerce_iterable_of_strings(
    value: Any, sim_id: str, field_path: str, allow_none: bool = False
) -> Tuple[str, ...] | None:
    if value is None and allow_none:
        return None
    if isinstance(value, (str, bytes)):
        raise ScenarioError(
            f"Simulator {sim_id} returned invalid META: {field_path} must be a "
            "sequence of strings, got str."
        )
    if value is None:
        return tuple()
    if isinstance(value, Mapping) or not isinstance(value, Iterable):
        raise ScenarioError(
            f"Simulator {sim_id} returned invalid META: {field_path} must be a "
            "sequence of strings, "
            f"got {type(value).__name__}."
        )

    coerced = []
    for idx, element in enumerate(value):
        if not isinstance(element, str):
            raise ScenarioError(
                f"Simulator {sim_id} returned invalid META: {field_path}[{idx}] must "
                f"be a string, got {type(element).__name__}."
            )
        coerced.append(element)
    return tuple(coerced)
