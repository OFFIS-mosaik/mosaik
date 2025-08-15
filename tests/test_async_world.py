import asyncio

import pytest

from mosaik.async_scenario import AsyncWorld
from mosaik.scenario import SimConfig
from mosaik.starters import CmdStarter, PythonStarter
from tests.simulators.generic_test_simulator import TestSim as GenericSim


@pytest.mark.asyncio
async def test_async_world():
    sim_config: SimConfig = {
        "Python": {"python": "tests.simulators.generic_test_simulator:TestSim"},
        "Cmd": {
            "cmd": "%(python)s -m tests.simulators.generic_test_simulator %(addr)s"
        },
    }

    world = AsyncWorld(sim_config, mosaik_config={"addr": ("127.0.0.1", None)})

    await world.start("Python")
    await world.start("Cmd")

    await asyncio.gather(
        world.start("Cmd"),
        world.start("Cmd"),
    )

    await world.shutdown()


@pytest.mark.asyncio
async def test_direct_starters():
    async with AsyncWorld() as world:
        test_sim = await world.start(PythonStarter(GenericSim), "TestSim")
        assert test_sim._sid == "TestSim"
        assert type(test_sim._proxy.sim) is GenericSim
        cmd_sim = await world.start(
            CmdStarter(
                cmd="%(python)s -m tests.simulators.generic_test_simulator %(addr)s",
                bind_addr=("", 0),
                connect_timeout=0,
            ),
            "CmdSim",
        )
        assert cmd_sim._sid == "CmdSim"
