"""
Scenario 28:
   A → B → C → D

This scenario tests for the right max_advance value if an earlier step is
inserted.
"""


from mosaik import World


def create_scenario(world: World):
    model_a = world.start(
        "Generic", sim_id="A", step_type="event-based", self_steps={0: 1, 1: 2}
    ).A()
    model_b = world.start(
        "Generic", sim_id="B", step_type="event-based", self_steps={0: 3}
    ).A()
    model_c = world.start("Generic", sim_id="C", step_type="event-based").A()
    model_d = world.start("Generic", sim_id="D", step_type="event-based").A()
    world.connect(model_a, model_b, ("val_out", "val_in"))
    world.connect(model_b, model_c, ("val_out", "val_in"))
    world.connect(model_b, model_d, ("val_out", "val_in"))
    world.connect(model_c, model_d, ("val_out", "val_in"))
    world.set_initial_event(model_a.sid, 0)
    world.set_initial_event(model_b.sid, 0)


def test_scenario(world: World):
    create_scenario(world)
    world.run(until=4)

    world.assert_graph(
        """
        A~0 A~1
        A~0 B~0
        B~0 B~3
        B~0 C~0
        B~0 D~0
        C~0 D~0
        A~1 A~2
        A~1 B~1
        B~1 C~1
        B~1 D~1
        C~1 D~1
        A~2 B~2
        B~2 C~2
        B~2 D~2
        C~2 D~2
        B~3 C~3
        B~3 D~3
        C~3 D~3
        """
    )

    world.assert_inputs(
        {
            "B~0": {"0": {"val_in": {"A.0": 0}}},
            "C~0": {"0": {"val_in": {"B.0": 0}}},
            "D~0": {"0": {"val_in": {"B.0": 0, "C.0": 0}}},
            "B~1": {"0": {"val_in": {"A.0": 1}}},
            "C~1": {"0": {"val_in": {"B.0": 1}}},
            "D~1": {"0": {"val_in": {"B.0": 1, "C.0": 1}}},
            "B~2": {"0": {"val_in": {"A.0": 2}}},
            "C~2": {"0": {"val_in": {"B.0": 2}}},
            "D~2": {"0": {"val_in": {"B.0": 2, "C.0": 2}}},
            "C~3": {"0": {"val_in": {"B.0": 3}}},
            "D~3": {"0": {"val_in": {"B.0": 3, "C.0": 3}}},
        }
    )
