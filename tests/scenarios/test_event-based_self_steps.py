"""
Scenario 19::
   A() → B() → C()
"""

from mosaik import World


def create_scenario(world: World):
    model_a = world.start(
        "Generic",
        sim_id="A",
        step_type="event-based",
        self_steps={0: 2},
        output_timing={0: 0},
    ).A()
    model_b = world.start("Generic", sim_id="B", step_type="event-based").A()
    model_c = world.start(
        "Generic", sim_id="C", step_type="event-based", self_steps={0: 3}
    ).A()
    world.connect(model_a, model_b, ("val_out", "val_in"))
    world.connect(model_b, model_c, ("val_out", "val_in"))
    world.set_initial_event(model_a.sid)


def test_scenario(world: World):
    create_scenario(world)
    world.run(until=4)

    world.assert_graph(
        """
        A~0 A~2
        A~0 B~0
        B~0 C~0
        C~0 C~3
        """
    )

    world.assert_inputs(
        {
            "B~0": {"0": {"val_in": {"A.0": 0}}},
            "C~0": {"0": {"val_in": {"B.0": 0}}},
            "C~3": {},
        }
    )
