"""
Scenario 25:
   A → B ⇄ C

This scenario tests for a specific deadlock in cyclic dependencies.
"""

import pytest

from mosaik import World


@pytest.mark.weak
def create_scenario(world: World):
    model_a = world.start(
        "Generic",
        sim_id="A",
        step_type="event-based",
        self_steps={0: 1},
        output_timing={},
    ).A()
    with world.group():
        model_b = world.start(
            "Generic",
            sim_id="B",
            step_type="event-based",
            self_steps={},
            output_timing={},
        ).A()
        model_c = world.start("Generic", sim_id="C", step_type="event-based").A()
    world.connect(model_a, model_b, ("val_out", "val_in"))
    world.connect(model_b, model_c, ("val_out", "val_in"))
    world.connect(model_c, model_b, ("val_out", "val_in"), weak=True)
    world.set_initial_event(model_a.sid, 0)
    world.set_initial_event(model_b.sid, 0)


def test_scenario(world: World):
    create_scenario(world)
    world.run(until=7)

    world.assert_graph(
        """
        A~0 A~1
        """,
        extra_nodes=["B~0:0"],
    )

    world.assert_inputs(
        {
            "B~0:0": {},
        }
    )
