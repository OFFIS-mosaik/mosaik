import warnings
from mosaik_api_v3.connection import RemoteException
import pytest
from mosaik import simmanager
from mosaik.exceptions import ScenarioError

from mosaik.scenario import SimConfig, World


sim_config: SimConfig = {
    "MetaMirror": {
        "python": "tests.simulators.meta_mirror:MetaMirror",
    },
    "MetaMirror2.0": {
        "python": "tests.simulators.meta_mirror:MetaMirror",
        "api_version": "2.0",
    },
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
                "MetaMirror",
                "MetaMirror-0",
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
                "MetaMirror2.0",
                "MetaMirror-0",
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
                "MetaMirror",
                "MetaMirror-0",
                time_resolution=1.0,
                sim_params={"meta": {"api_version": "1000.0"}},
            )
        )

    assert str(exc_info.value) == (
        "There was an error during the initialization of MetaMirror-0: The API version "
        "(1000.0) is too new for this version of mosaik. Maybe a newer version of the "
        "mosaik package is available to be used in your scenario?"
    )


def test_exception_in_async_request(world: World, caplog):  # noqa: F811
    """Exception in calls back to mosaik should be surfaced in the
    calling simulator and result in a warning on the mosaik side.
    """
    sim = world.start("RemoteGeneric")
    with caplog.at_level(30):
        # This would raise if the expected KeyError were not raised
        sim.call_mosaik_method("get_related_entities", ("does_not_exist",), "KeyError")
        # But we should see the error as a warning in mosaik's logs
        assert "KeyError('does_not_exist')" in caplog.text

    # If we don't specify an expected exception for the
    # `call_mosaik_method` call, the exception should get back to us.
    with pytest.raises(RemoteException) as exc_info:
        sim.call_mosaik_method("get_related_entities", ("does_not_exist",))
    assert exc_info.value.remote_type == "RemoteException"
