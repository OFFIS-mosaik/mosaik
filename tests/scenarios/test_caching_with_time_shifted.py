from mosaik import World


def create_scenario(world: World):
    model_a = world.start("Generic", sim_id="A").A()
    model_b = world.start("Generic", sim_id="B").A()
    model_c = world.start("Generic", sim_id="C").A()

    world.connect(
        model_a,
        model_b,
        ("val_out", "val_in"),
        time_shifted=True,
        initial_data={"val_out": -1},
    )
    world.connect(
        model_b,
        model_a,
        ("val_out", "val_in"),
        time_shifted=True,
        initial_data={"val_out": -1},
    )
    world.connect(model_a, model_c, ("val_out", "val_in"))
    world.connect(model_c, model_b, ("val_out", "val_in"))


def test_scenario(world: World):
    create_scenario(world)
    world.run(until=2)

    world.assert_graph(
        """
        A~0 A~1
        A~0 B~1
        A~0 C~0
        B~0 B~1
        B~0 A~1
        C~0 C~1
        C~0 B~0
        A~1 C~1
        C~1 B~1
        """
    )

    world.assert_inputs(
        {
            "A~0": {"0": {"val_in": {"B.0": -1}}},
            "A~1": {"0": {"val_in": {"B.0": 0}}},
            "C~0": {"0": {"val_in": {"A.0": 0}}},
            "B~0": {"0": {"val_in": {"C.0": 0, "A.0": -1}}},
            "B~1": {"0": {"val_in": {"A.0": 0, "C.0": 1}}},
            "C~1": {"0": {"val_in": {"A.0": 1}}},
        }
    )
