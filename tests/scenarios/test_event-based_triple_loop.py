"""
Scenario 17::
   A() → B() → C() → A()
"""

import pytest

from mosaik import World


def create_scenario(world: World):
    with world.group():
        model_a = world.start(
            "Generic", sim_id="A", step_type="event-based", output_timing={0: 2}
        ).A()
        model_b = world.start(
            "Generic", sim_id="B", step_type="event-based", output_timing={2: 3}
        ).A()
        model_c = world.start(
            "Generic", sim_id="C", step_type="event-based", output_timing={3: 5}
        ).A()
    world.connect(model_a, model_b, ("val_out", "val_in"))
    world.connect(model_b, model_c, ("val_out", "val_in"))
    world.connect(model_c, model_a, ("val_out", "val_in"), weak=True)
    world.set_initial_event(model_a.sid)


@pytest.mark.weak
def test_scenario(world: World):
    create_scenario(world)
    world.run(until=6)

    world.assert_graph(
        """
        A~0:0 B~2:0
        B~2:0 C~3:0
        C~3:0 A~5:1
        """
    )

    world.assert_inputs(
        {
            "B~2:0": {"0": {"val_in": {"A.0": 0}}},
            "C~3:0": {"0": {"val_in": {"B.0": 2}}},
            "A~5:1": {"0": {"val_in": {"C.0": 3}}},
        }
    )
