import pytest

import mosaik
import mosaik.basic_simulators
import mosaik.util
from mosaik.scenario import SimConfig


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
        test_model[0], test_model[1], ("value", "to_be_deleted"), time_shifted=True
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
        test_model[0], test_model[1], ("value", "to_be_deleted"), time_shifted=True
    )
    world.set_initial_event(test_sim._sid, 0)

    with pytest.warns(UserWarning, match="returned data for attribute"):
        world.run(until=END)
