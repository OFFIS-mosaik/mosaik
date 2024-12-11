"""
Scenario 26:
   A ⇄ B ⇄ C

This scenario tests for chained cyclic dependencies.
"""

import pytest

from mosaik import World


def create_scenario(world: World):
    with world.group():
        model_a = world.start(
            "RemoteGeneric",
            sim_id="A",
            step_type="event-based",
            self_steps={0: 4},
            output_timing={0: 0},
        ).A()
        model_b = world.start(
            "RemoteGeneric",
            sim_id="B",
            step_type="event-based",
            self_steps={0: 2},
            output_timing={0: 0},
        ).A()
        model_c = world.start("RemoteGeneric", sim_id="C", step_type="event-based").A()
    world.connect(model_a, model_b, ("val_out", "val_in"))
    world.connect(model_b, model_a, ("val_out", "val_in"), weak=True)
    world.connect(model_b, model_c, ("val_out", "val_in"))
    world.connect(model_c, model_b, ("val_out", "val_in"), weak=True)
    world.set_initial_event(model_b.sid, 0)


@pytest.mark.weak
def test_scenario(world: World):
    create_scenario(world)
    world.run(until=7)

    world.assert_graph(
        """
        B~0:0 B~2:0
        B~0:0 A~0:1
        B~0:0 C~0:0
        A~0:1 A~4:0
        A~0:1 B~0:1
        C~0:0 B~0:1
        B~0:1 B~2:0
        """
    )

    world.assert_inputs(
        {
            "A~0:1": {"0": {"val_in": {"B.0": 0}}},
            "C~0:0": {"0": {"val_in": {"B.0": 0}}},
            "B~0:1": {"0": {"val_in": {"A.0": 0, "C.0": 0}}},
        }
    )
