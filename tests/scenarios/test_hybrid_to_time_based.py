"""
Scenario 12::
   A() → B(2)
"""

from mosaik import World


def create_scenario(world: World):
    model_a = world.start(
        "Generic", sim_id="A", step_type="hybrid", self_steps={0: 1, 1: 3}
    ).A()
    model_b = world.start("Generic", sim_id="B", step_size=2).A()
    world.set_initial_event(model_a.sid)
    world.connect(model_a, model_b, ("val_out", "val_in"))


def test_scenario(world: World):
    create_scenario(world)
    world.run(until=3)

    world.assert_graph(
        """
        A~0 A~1
        A~0 B~0
        B~0 B~2
        A~1 B~2
        """
    )

    world.assert_inputs(
        {
            "B~0": {"0": {"val_in": {"A.0": 0}}},
            "B~2": {"0": {"val_in": {"A.0": 1}}},
        }
    )
