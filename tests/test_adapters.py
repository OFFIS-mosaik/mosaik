import warnings

import pytest
import pytest_asyncio

from mosaik.async_scenario import AsyncWorld
from mosaik.exceptions import ScenarioError
from mosaik.scenario import SimConfig

sim_config: SimConfig = {
    "MetaMirror": {
        "python": "tests.simulators.meta_mirror:MetaMirror",
    },
    "MetaMirror2.0": {
        "python": "tests.simulators.meta_mirror:MetaMirror",
        "api_version": "2.0",
    },
}


@pytest_asyncio.fixture(name="world")
async def world_fixture():
    async with AsyncWorld(sim_config) as world:
        yield world


@pytest.mark.asyncio
async def test_old_api_version_warning(world: AsyncWorld):
    # There should be a warning if an old API version is used without
    # specifying it.
    with pytest.warns(UserWarning, match="outdated API version"):
        await world.start(
            "MetaMirror",
            meta={"api_version": "2.0", "models": {}},
        )


@pytest.mark.asyncio
async def test_old_api_version_no_warning(world: AsyncWorld):
    # Specifying an API version in the sim_config should suppress the
    # warning.
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        await world.start(
            "MetaMirror2.0",
            meta={"api_version": "2.0", "models": {}},
        )


@pytest.mark.asyncio
async def test_start_wrong_api_version(world: AsyncWorld):
    """
    An exception should be raised if the simulator uses an unsupported
    API version."""
    with pytest.raises(ScenarioError) as exc_info:
        await world.start(
            "MetaMirror",
            meta={"api_version": "1000.0", "models": {}},
        )

    assert str(exc_info.value) == (
        "There was an error during the initialization of MetaMirror-0: The API version "
        "(1000.0) is too new for this version of mosaik. Maybe a newer version of the "
        "mosaik package is available to be used in your scenario?"
    )
