"""
Scenario 21::
   A() → B() → C()
"""

import pytest

from mosaik import World


def create_scenario(world: World):
    with world.group():
        model_a = world.start(
            "Generic",
            sim_id="A",
            step_type="event-based",
            self_steps={0: 2},
            output_timing={},
        ).A()
        model_b = world.start("Generic", sim_id="B", step_type="event-based").A()
        model_c = world.start(
            "Generic", sim_id="C", step_type="hybrid", self_steps={0: 3}
        ).A()
    world.connect(model_a, model_b, ("val_out", "val_in"))
    world.connect(model_b, model_c, ("val_out", "val_in"))
    world.connect(
        model_c, model_a, ("val_out", "val_in"), weak=True, initial_data={"val_out": -1}
    )
    world.set_initial_event(model_a.sid)


@pytest.mark.weak
def test_scenario(world: World):
    create_scenario(world)
    world.run(until=4)

    world.assert_graph(
        """
        A~0:0 A~2:0
        C~0:0 C~3:0
        C~0:0 A~0:1
        A~0:1 A~2:0
        C~0:0 A~2:0
        C~3:0 A~3:1
        """
    )

    world.assert_inputs(
        {
            "A~0:0": {"0": {"val_in": {"C.0": -1}}},
            "A~0:1": {"0": {"val_in": {"C.0": 0}}},
            "A~2:0": {"0": {"val_in": {"C.0": 0}}},
            "A~3:1": {"0": {"val_in": {"C.0": 3}}},
        }
    )
