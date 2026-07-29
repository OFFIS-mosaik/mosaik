"""
Scenario 3::

    A(2) → B(1)
"""

from mosaik import World


def create_scenario(world: World):
    model_a = world.start("Generic", sim_id="A").A()
    model_b = world.start(
        "Generic", sim_id="B", step_type="event-based", self_steps={0: 2}
    ).A()
    world.connect(model_a, model_b, ("val_out", "val_in"))


def test_scenario(world: World):
    create_scenario(world)
    world.run(until=3)

    world.assert_graph(
        """
        A~0 A~1
        A~0 B~0
        B~0 B~2
        A~1 A~2
        A~1 B~1
        A~2 B~2
        """
    )

    world.assert_inputs(
        {
            "B~0": {"0": {"val_in": {"A.0": 0}}},
            "B~1": {"0": {"val_in": {"A.0": 1}}},
            "B~2": {"0": {"val_in": {"A.0": 2}}},
        }
    )
