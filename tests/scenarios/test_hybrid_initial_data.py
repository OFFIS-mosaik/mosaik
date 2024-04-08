"""
Scenario 21::
   A() ⇄ B()

This scenario tests if the data provided in initial_data is sent correcntly from a hybrid simulator to a
time-based simulator
"""


from mosaik import World


def create_scenario(world: World):
    model_a = world.start("Generic", sim_id="A", step_type="time-based").A()
    model_b = world.start(
        "Generic", sim_id="B", step_type="hybrid", self_steps={0: 1}
    ).A()
    world.connect(model_a, model_b, ("val_out", "val_in"))
    world.connect(
        model_b,
        model_a,
        ("val_out", "val_in"),
        time_shifted=True,
        initial_data={"val_out": -1},
    )


def test_scenario(world: World):
    create_scenario(world)
    world.run(until=2)

    world.assert_graph(
        """
        A~0 A~1
        A~0 B~0
        B~0 A~1
        B~0 B~1
        A~1 B~1
        """
    )

    world.assert_inputs(
        {
            "A~0": {"0": {"val_in": {"B.0": -1}}},
            "A~1": {"0": {"val_in": {"B.0": 0}}},
            "B~0": {"0": {"val_in": {"A.0": 0}}},
            "B~1": {"0": {"val_in": {"A.0": 1}}},
        }
    )
