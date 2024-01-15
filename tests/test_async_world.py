import asyncio

import pytest

from mosaik.async_scenario import AsyncWorld
from mosaik.scenario import SimConfig


@pytest.mark.asyncio
async def test_async_world():
    sim_config: SimConfig = {
        "Python": {"python": "tests.simulators.generic_test_simulator:TestSim"},
        "Cmd": {"cmd": "%(python)s -m tests.simulators.generic_test_simulator %(addr)s"},
    }

    world = AsyncWorld(sim_config, mosaik_config={"addr": ("127.0.0.1", None)})
    
    sim_p = await world.start("Python")
    sim_c = await world.start("Cmd")

    sim_cs = await asyncio.gather(
        world.start("Cmd"),
        world.start("Cmd"),
    )

    await world.shutdown()
