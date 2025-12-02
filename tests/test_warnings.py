import pytest

import mosaik
import mosaik.basic_simulators
import mosaik.util
from mosaik.scenario import SimConfig
from mosaik.starters import PythonStarter
from tests.simulators.warnings_test_simulator import WarningsTestSimulator


def test_non_existing_entity_warning():
    SIM_CONFIG: SimConfig = {
        "WarningsTestSimulator": {
            "python": "tests.simulators.warnings_test_simulator:WarningsTestSimulator",
        },
    }

    END = 1

    world = mosaik.World(SIM_CONFIG)
    with world.group():
        test_sim = world.start("WarningsTestSimulator")

    test_sim.set_add_unregistered_entity(True)
    test_model = test_sim.Test.create(2)

    world.connect(
        test_model[0], test_model[1], ("value", "to_be_deleted"), time_shifted=1
    )
    world.set_initial_event(test_sim._sid, 0)

    with pytest.warns(UserWarning, match="returned data for the entity"):
        world.run(until=END)


def test_non_existing_attribute_warning():
    SIM_CONFIG: SimConfig = {
        "WarningsTestSimulator": {
            "python": "tests.simulators.warnings_test_simulator:WarningsTestSimulator",
        },
    }

    END = 1

    world = mosaik.World(SIM_CONFIG)
    with world.group():
        test_sim = world.start("WarningsTestSimulator")
    test_sim.set_add_unregistered_attr(True)
    test_model = test_sim.Test.create(2)

    world.connect(
        test_model[0], test_model[1], ("value", "to_be_deleted"), time_shifted=1
    )
    world.set_initial_event(test_sim._sid, 0)

    with pytest.warns(UserWarning, match="returned data for attribute"):
        world.run(until=END)


def test_time_shifted_events_warning():
    with mosaik.World() as world:
        sim = world.start(PythonStarter(WarningsTestSimulator), "TestSim")
        ent0, ent1 = sim.Test.create(2)
        with pytest.warns(UserWarning, match="implicit 1-step shift"):
            world.connect(ent0, ent1, "value", time_shifted=True)
