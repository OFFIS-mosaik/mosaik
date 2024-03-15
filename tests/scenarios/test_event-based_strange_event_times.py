"""
Scenario 18::
   A() → B()
"""

from mosaik import World


def create_scenario(world: World):
    model_a = world.start(
        "RemoteGeneric", sim_id="A", step_type="event-based", events={0.05: 1, 0.1: 2}
    ).A()
    model_b = world.start("RemoteGeneric", sim_id="B", step_type="event-based").A()
    world.connect(model_a, model_b, ("val_out", "val_in"))


def test_scenario(world: World):
    create_scenario(world)
    world.run(until=2, rt_factor=0.1)

    world.assert_graph(
        """
        A~1 B~1
        """
    )

    world.assert_inputs(
        {
            "B~1": {"0": {"val_in": {"A.0": 1}}},
        }
    )
