"""
Test a complete mosaik simulation using mosaik as a library.

"""
import importlib
import gc
import glob
import os
import sys
import time
from types import ModuleType
from typing import Any, Dict, List, Tuple
import warnings

from loguru import logger
import networkx as nx
import pytest
from tqdm import tqdm

from mosaik import scenario, _debug
from mosaik.tiered_time import TieredTime

from tests.scenarios.conftest import SIM_CONFIG


@pytest.mark.parametrize('sim_name', ["Local", "Remote"])
def test_call_extra_methods(sim_name: str):
    world = scenario.World(SIM_CONFIG)
    try:
        model_a = world.start(sim_name)
        ret = model_a.example_method(23)
    finally:
        world.shutdown()

    assert ret == 23


@pytest.mark.parametrize('sim_name', ["Generic", "RemoteGeneric"])
def test_call_two_extra_methods(sim_name: str):
    world = scenario.World(SIM_CONFIG)
    try:
        model_a = world.start(sim_name)
        ret_a1 = model_a.method_a(arg=23)
        ret_a2 = model_a.method_a(882)
        ret_b = model_a.method_b(val=42)
    finally:
        world.shutdown()

    assert ret_a1 == "method_a(23)"
    assert ret_a2 == "method_a(882)"
    assert ret_b == "method_b(42)"


def test_rt_sim():
    fixture = importlib.import_module('tests.scenarios.test_single_self_stepping')
    world = scenario.World(SIM_CONFIG)
    try:
        fixture.create_scenario(world)

        factor = 0.1
        start = time.perf_counter()
        world.run(until=fixture.UNTIL, rt_factor=factor)
        duration = (time.perf_counter() - start) / factor

        assert (fixture.UNTIL - 1) < duration < fixture.UNTIL
    finally:
        world.shutdown()


@pytest.mark.parametrize('strict', [True, False])
def test_rt_sim_too_slow(strict, caplog):
    fixture = importlib.import_module('tests.scenarios.test_single_self_stepping')
    world = scenario.World(SIM_CONFIG)
    try:
        fixture.create_scenario(world)

        factor = 0.00001
        if strict:
            pytest.raises(RuntimeError, world.run, until=fixture.UNTIL,
                          rt_factor=factor, rt_strict=strict)
        else:
            world.run(until=fixture.UNTIL, rt_factor=factor, rt_strict=strict)
            assert 'too slow for real-time factor' in caplog.text
    finally:
        world.shutdown()
