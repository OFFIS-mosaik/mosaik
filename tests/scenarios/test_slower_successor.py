"""
Scenario 4

    A(1) → B(2)
"""

from mosaik import World


def create_scenario(world: World):
    simulator_a = world.start("Local", sim_id="A")
    simulator_b = world.start("Local", sim_id="B", step_size=2)
    model_a = simulator_a.A(init_val=0)
    model_b = simulator_b.B(init_val=0)
    world.connect(model_a, model_b, ("val_out", "val_in"))


def test_scenario(world: World):
    create_scenario(world)
    world.run(until=4)

    world.assert_graph(
        """
        A~0 A~1
        A~0 B~0
        A~1 A~2
        A~2 A~3
        A~2 B~2
        B~0 B~2
        """
    )

    world.assert_inputs(
        {
            "B~0": {"0.0": {"val_in": {"A.0.0": 1}}},
            "B~2": {"0.0": {"val_in": {"A.0.0": 3}}},
        }
    )
