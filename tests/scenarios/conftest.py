import os
import sys

import pytest
from loguru import logger
from tqdm import tqdm

import mosaik

venv = os.path.dirname(sys.executable)

SIM_CONFIG: mosaik.SimConfig = {
    "Local": {"python": "example_sim.mosaik:ExampleSim"},
    "LocalMAS": {"python": "example_mas.mosaik:ExampleMas"},
    "Generic": {"python": "tests.simulators.generic_test_simulator:TestSim"},
    "LoopSim": {"python": "tests.simulators.loop_simulators.loop_simulator:LoopSim"},
    "FixedOut": {"python": "tests.simulators.fixed_output_sim:FixedOutputSim"},
    "EchoSim": {"python": "tests.simulators.loop_simulators.echo_simulator:EchoSim"},
    "Remote": {"cmd": f"{venv}/pyexamplesim %(addr)s"},
    "RemoteMAS": {"cmd": f"{venv}/pyexamplemas %(addr)s"},
    "RemoteGeneric": {
        "cmd": "%(python)s tests/simulators/generic_test_simulator.py %(addr)s"
    },
}


@pytest.fixture(params=[True, False])
def world(request: pytest.FixtureRequest):
    logger.remove()
    logger.add(lambda msg: tqdm.write(msg, end=""), colorize=True)
    cache: bool = request.param

    world = mosaik.World(SIM_CONFIG, debug=True, cache=cache)
    yield world
    world.shutdown()
