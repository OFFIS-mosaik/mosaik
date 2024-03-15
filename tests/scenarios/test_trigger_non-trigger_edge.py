"""
In this scenario, we add two edges between the same simulators, one trigger,
one non-trigger. The second edge's non-triggering behaviour should not
overwrite the first edges triggering behaviour.
"""

from mosaik import World


def create_scenario(world: World):
    sim_0 = world.start("Generic", sim_id="A", step_size=1)
    ent_0 = sim_0.A()

    sim_1 = world.start(
        "Generic", sim_id="B", step_type="hybrid", trigger=["trigger_in"]
    )
    ent_1 = sim_1.A()

    world.connect(ent_0, ent_1, ("val_out", "trigger_in"))
    world.connect(ent_0, ent_1, ("val_out", "val_in"))


def test_scenario(world: World):
    create_scenario(world)
    world.run(until=2)

    world.assert_graph(
        """
        A~0 B~0
        A~0 A~1
        A~1 B~1
        """
    )

    world.assert_inputs(
        {
            "B~0": {"0": {"trigger_in": {"A.0": 0}, "val_in": {"A.0": 0}}},
            "B~1": {"0": {"trigger_in": {"A.0": 1}, "val_in": {"A.0": 1}}},
        }
    )
