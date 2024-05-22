"""
Scenario 13::
   A() → B()
"""

from mosaik import World


def create_scenario(world: World):
    model_a = world.start(
        "Generic",
        sim_id="A",
        step_type="event-based",
        self_steps={0: 1, 1: 3},
        output_timing={0: 0, 1: None},
    ).A()
    model_b = world.start("Generic", sim_id="B", step_type="event-based").A()
    world.set_initial_event(model_a.sid)
    world.connect(model_a, model_b, ("val_out", "val_in"))


def test_scenario(world: World):
    create_scenario(world)
    world.run(until=3)

    world.assert_graph(
        """
        A~0 A~1
        A~0 B~0
        """
    )

    world.assert_inputs(
        {
            "B~0": {"0": {"val_in": {"A.0": 0}}},
        }
    )
