from typing import Any, Dict, cast

import mosaik
import mosaik.basic_simulators
from mosaik.basic_simulators.input_simulator import InputSimulator
from mosaik.simmanager import SimRunner
import mosaik.util
from mosaik.scenario import SimConfig


def test_non_existing_entity_warning():
    # Sim config. and other parameters
    SIM_CONFIG: SimConfig = {
        "TestSimulator": {
            "python": "mosaik.basic_simulators.test_simulator:TestSimulator",
        },
    }

    END = 15  # 15 seconds

    world = mosaik.World(SIM_CONFIG)
    with world.group():
        test_sim = world.start("TestSimulator")

    test_model = test_sim.Test.create(2)

    world.connect(
        test_model[0], test_model[1], ("value", "to_be_deleted"), time_shifted=True
    )

    world.run(until=END)


test_non_existing_entity_warning()
