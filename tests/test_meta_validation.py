from copy import deepcopy

import pytest

from mosaik.exceptions import ScenarioError
from mosaik.scenario import SimConfig, World

BASE_META = {
    "api_version": "3.0",
    "type": "time-based",
    "models": {
        "Model": {
            "public": True,
            "params": ["param_1"],
            "attrs": ["attr_1"],
        },
    },
    "extra_methods": [],
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


def test_meta_validation_rejects_non_mapping_models(world: World):
    meta = deepcopy(BASE_META)
    meta["models"] = []

    with pytest.raises(ScenarioError, match=r"meta\['models'] must be a mapping"):
        world.start("MetaMirror", meta=meta)


def test_meta_validation_rejects_non_sequence_params(world: World):
    meta = deepcopy(BASE_META)
    meta["models"]["Model"]["params"] = "param_1"

    with pytest.raises(
        ScenarioError, match=r"meta\['models'\]\['Model']\['params'] must be a sequence"
    ):
        world.start("MetaMirror", meta=meta)


def test_meta_validation_rejects_non_string_extra_method(world: World):
    meta = deepcopy(BASE_META)
    meta["extra_methods"] = ["method_a", 123]

    with pytest.raises(
        ScenarioError, match=r"meta\['extra_methods']\[1] must be a string"
    ):
        world.start("MetaMirror", meta=meta)
