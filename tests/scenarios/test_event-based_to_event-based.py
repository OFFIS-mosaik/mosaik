"""
Scenario 9::
   A() → B()
"""


from mosaik import World


def create_scenario(world: World):
    model_a = world.start(
        "Generic", sim_id="A", step_type="event-based", output_timing={0: 2}
    ).A()
    model_b = world.start("Generic", sim_id="B", step_type="event-based").A()
    world.connect(model_a, model_b, ("val_out", "val_in"))
    world.set_initial_event(model_a.sid)


def test_scenario(world: World):
    create_scenario(world)
    world.run(until=3)

    world.assert_graph(
        """
        A~0 B~2
        """
    )

    world.assert_inputs(
        {
            "B~2": {"0": {"val_in": {"A.0": 0}}},
        }
    )
