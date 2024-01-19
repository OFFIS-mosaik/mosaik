import warnings
import pytest
from mosaik import simmanager
from mosaik.exceptions import ScenarioError

from mosaik.scenario import SimConfig, World


sim_config: SimConfig = {
    "MetaMock": {
        "python": "tests.mocks.meta_mock:MetaMock",
    },
    "MetaMock2.0": {
        "python": "tests.mocks.meta_mock:MetaMock",
        "api_version": "2.0",
    }
}


@pytest.fixture(name="world")
def world_fixture():
    world = World(sim_config)
    yield world
    world.shutdown()


def test_old_api_version_warning(world: World):
    # There should be a warning if an old API version is used without
    # specifying it.
    with pytest.warns(UserWarning, match="outdated API version"):
        world.loop.run_until_complete(
            simmanager.start(
                world,
                "MetaMock",
                "MetaMock-0",
                time_resolution=1.0,
                sim_params={"meta": {"api_version": "2.0"}},
            )
        )


def test_old_api_version_no_warning(world: World):
    # Specifying an API version in the sim_config should suppress the
    # warning.
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        world.loop.run_until_complete(
            simmanager.start(
                world,
                "MetaMock2.0",
                "MetaMock-0",
                time_resolution=1.0,
                sim_params={"meta": {"api_version": "2.0"}},
            )
        )

    
def test_start_wrong_api_version(world: World):
    """
    An exception should be raised if the simulator uses an unsupported
    API version."""
    with pytest.raises(ScenarioError) as exc_info:
        world.loop.run_until_complete(
            simmanager.start(
                world,
                "MetaMock",
                "MetaMock-0",
                time_resolution=1.0,
                sim_params={"meta": {"api_version": "1000.0"}},
            )
        )

    assert str(exc_info.value) == (
        "There was an error during the initialization of MetaMock-0: The API version "
        "(1000.0) is too new for this version of mosaik. Maybe a newer version of the "
        "mosaik package is available to be used in your scenario?"
    )


