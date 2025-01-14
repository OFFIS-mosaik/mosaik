import warnings
from io import StringIO

import pytest
from loguru import logger

import mosaik
import mosaik.basic_simulators
import mosaik.util
from mosaik.scenario import SimConfig


def test_non_existing_entity_warning():
    SIM_CONFIG: SimConfig = {
        "TestSimulator": {
            "python": "mosaik.basic_simulators.test_simulator:TestSimulator",
        },
    }

    END = 1

    world = mosaik.World(SIM_CONFIG)
    with world.group():
        test_sim = world.start("TestSimulator")

    test_sim.set_add_unregistered_entity(True)
    test_model = test_sim.Test.create(2)

    world.connect(
        test_model[0], test_model[1], ("value", "to_be_deleted"), time_shifted=True
    )

    world.run(until=END)
    with pytest.warns(UserWarning):
        warnings.warn(
            "Simulator TestSimulator-0 returned data"
            "for the entity non_existing_eid which was never created."
            "This is likely an error in its get_data method.",
            UserWarning,
        )


def test_non_existing_attribute_warning():
    log_output = StringIO()
    logger.add(log_output, format="{message}", level="WARNING")
    SIM_CONFIG: SimConfig = {
        "TestSimulator": {
            "python": "mosaik.basic_simulators.test_simulator:TestSimulator",
        },
    }

    END = 1

    world = mosaik.World(SIM_CONFIG)
    with world.group():
        test_sim = world.start("TestSimulator")
    test_sim.set_add_unregistered_attr(True)
    test_model = test_sim.Test.create(2)

    world.connect(
        test_model[0], test_model[1], ("value", "to_be_deleted"), time_shifted=True
    )

    world.run(until=END)
    with pytest.warns(UserWarning):
        warnings.warn(
            "The attribute non_existing_attr does not exist in model Test. "
            "Data will not be transferred.",
            UserWarning,
        )
