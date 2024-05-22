"""
In this scenario we have two simulators, the first simulator has two outputs,
one is connected to the trigger input and one is connected to the
non-trigger input of the other simulator. Then an output of the first simulator
triggers on the second attribute of the other simulator, although the input is
non-trigger.
"""

from mosaik import World


def create_scenario(world: World):
    sim_0 = world.start("Generic", sim_id="A", step_size=1)
    ent_0 = sim_0.A()

    sim_1 = world.start(
        "Generic", sim_id="B", step_type="hybrid", trigger=["trigger_in"]
    )
    ent_1 = sim_1.A()

    world.connect(ent_0, ent_1, ("never_out", "trigger_in"), ("val_out", "val_in"))


def test_scenario(world: World):
    create_scenario(world)
    world.run(until=2)

    world.assert_graph(
        """
        A~0 B~0
        A~0 A~1
        """
    )

    world.assert_inputs(
        {
            "B~0": {"0": {"trigger_in": {"A.0": None}, "val_in": {"A.0": 0}}},
        }
    )
