from copy import deepcopy
from typing import Literal, Optional, Tuple, Union, cast

import pytest
from mosaik_api_v3.types import (
    Meta,
    ModelDescription,
)
from typing_extensions import Type

from mosaik.in_or_out_set import OutSet
from mosaik.scenario import ModelMock, SimConfig, World, parse_attrs

META: Meta = {
    "api_version": "3.0",
    "type": "hybrid",
    "models": {
        "ModelName": {
            "public": True,
            "params": ["param_1"],
            "attrs": ["attr_1", "attr_2"],
        },
    },
}

SIM_CONFIG: SimConfig = {
    "MetaMirror": {
        "python": "tests.simulators.meta_mirror:MetaMirror",
    },
}


@pytest.fixture(name="world")
def world_fixture():
    world = World(SIM_CONFIG)
    yield world
    world.shutdown()


# Use parametrization to test many different cases. To make the
# descriptions more compact, we use single-letter attributes here, so
# the string "abc" actually represents the attribute list
# ["a", "b", "c"] (or the set frozenset({"a", "b", "c"}) for results
# of parse_attrs). To represent an ``OutSet``, we use a tilde at the
# beginning of the string, i.e. "~ab" represents OutSet({"a", "b"}).
# Each line represents a test case consisting of
# - the type of simulator
# - the any_inputs field
# - the attrs field (None if not specified)
# - a tuple of non-trigger, trigger, persistent, non-persitent fields
#   (each None if not specified and in this order to match parse_attrs'
#   result)
# - a tuple of measurement inputs, event inputs, measurement outputs,
#   event outputs; or an error type if the case should throw
@pytest.mark.parametrize(
    ("type", "any_inputs", "attrs", ("spec_in"), "spec_out"),
    [
        ("time-based", True, "ab", (None, None, None, None), ("~", "", "ab", "")),
        ("time-based", False, None, ("ab", "cd", None, "a"), ValueError),
        ("hybrid", True, None, ("ab", None, "c", "d"), ("ab", "~ab", "c", "d")),
        ("hybrid", False, None, ("a", "b", "c", None), ("a", "b", "c", "")),
        ("event-based", False, None, (None, "a", None, "b"), ("", "a", "", "b")),
        ("time-based", False, None, ("a", None, "b", None), ("a", "", "b", "")),
        ("hybrid", False, None, ("a", "b", "c", "d"), ("a", "b", "c", "d")),
        ("event-based", False, None, ("", "a", None, None), ValueError),
        ("time-based", False, "ab", (None, "a", None, None), ValueError),
        ("time-based", False, None, (None, None, None, None), ValueError),
        ("event-based", False, "ab", ("a", None, None, None), ValueError),
        ("time-based", False, "ab", (None, None, None, "a"), ValueError),
        ("event-based", False, "ab", (None, None, "a", None), ValueError),
        ("hybrid", False, "ab", (None, None, "a", "a"), ValueError),
        ("hybrid", False, "ab", ("a", "a", None, None), ValueError),
        ("hybrid", False, "iton", (None, None, None, ""), ("iton", "", "iton", "")),
    ],
)
def test_parse_attrs(
    type: Literal["time-based", "event-based", "hybrid"],
    any_inputs: bool,
    attrs: Optional[str],
    spec_in: Tuple[Optional[str], Optional[str], Optional[str], Optional[str]],
    spec_out: Union[Type[ValueError], Tuple[str, str, str, str]],
):
    model_description: ModelDescription = {
        "public": True,
        "params": [],
        "any_inputs": any_inputs,
    }  # type: ignore # We're creating the description "piece-meal"
    for field, value in (
        ("attrs", attrs),
        ("non-trigger", spec_in[0]),
        ("trigger", spec_in[1]),
        ("persistent", spec_in[2]),
        ("non-persistent", spec_in[3]),
    ):
        if value is not None:
            model_description[field] = list(value)  # type: ignore

    print(f"{type=}, {any_inputs=}, {attrs=}")
    print(f"(nt,  t,  p, np)={spec_in}")
    print(f"(mi, ei, mo, eo)={spec_out}")
    if isinstance(spec_out, tuple):
        out_sets = tuple(
            (
                OutSet(value[1:]) if value.startswith("~") else frozenset(value)
                for value in spec_out
            )
        )
        assert out_sets == parse_attrs(model_description, type)
    else:
        with pytest.raises(spec_out):
            parse_attrs(model_description, type)


def test_parse_attr_result_is_assigned_correctly(world: World):
    new_meta = deepcopy(META)
    del new_meta["models"]["ModelName"]["attrs"]
    new_meta["models"]["ModelName"]["trigger"] = []
    new_meta["models"]["ModelName"]["non-trigger"] = ["attr_1"]
    new_meta["models"]["ModelName"]["non-persistent"] = ["attr_2"]
    new_meta["models"]["ModelName"]["persistent"] = ["attr_3"]
    model = cast(ModelMock, world.start("MetaMirror", meta=new_meta).ModelName)
    assert model.measurement_inputs == frozenset(["attr_1"])
    assert model.event_inputs == frozenset()
    assert model.measurement_outputs == frozenset(["attr_3"])
    assert model.event_outputs == frozenset(["attr_2"])
    assert model.input_attrs == frozenset(["attr_1"])
    assert model.output_attrs == frozenset(["attr_2", "attr_3"])


def test_parse_attr_result_called_by_world_start(world: World):
    new_meta = deepcopy(META)
    new_meta["type"] = "time-based"
    new_meta["models"]["ModelName"]["trigger"] = ["attr_1"]
    with pytest.raises(ValueError):
        world.start("MetaMirror", meta=new_meta)
