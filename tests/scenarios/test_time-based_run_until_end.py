"""
Scenario 29:
   A → B

This scenario tests that self-stepping simulators run until they're done even
if their successors have already finished. This is a change in the intended
behaviour.
"""


from mosaik import World


def create_scenario(world: World):
    model_a = world.start("Generic", sim_id="A", step_size=1).A()
    model_b = world.start("Generic", sim_id="B", step_type="hybrid").A()
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
        """
    )

    world.assert_inputs(
        {
            "B~0": {"0": {"val_in": {"A.0": 0}}},
        }
    )
