"""
Scenario 23:
   A → B → C

This scenario tests for a deadlock caused by lazy_stepping if event-based
successor is not triggered.
"""

from mosaik import World


def create_scenario(world: World):
    model_a = world.start(
        "Generic", sim_id="A", step_type="time-based", step_size=3, output_timing={0: 0}
    ).A()
    model_b = world.start(
        "Generic",
        sim_id="B",
        step_type="event-based",
        self_steps={0: 2},
        output_timing={},
    ).A()
    model_c = world.start("Generic", sim_id="C", step_type="event-based").A()
    world.connect(model_a, model_b, ("val_out", "val_in"))
    world.connect(model_a, model_c, ("val_out", "val_in"))
    world.connect(model_b, model_c, ("val_out", "val_in"))
    world.set_initial_event(model_b.sid, 1)
    world.set_initial_event(model_c.sid, 1)


def test_scenario(world: World):
    create_scenario(world)
    world.run(until=7)

    world.assert_graph(
        """
        A~0 A~3
        A~0 C~0
        A~0 B~0
        A~0 C~1
        A~0 B~1
        A~0 B~2
        B~0 B~2
        A~3 A~6
        """
    )

    world.assert_inputs(
        {
            "B~0": {"0": {"val_in": {"A.0": 0}}},
            "C~0": {"0": {"val_in": {"A.0": 0}}},
            "B~1": {"0": {"val_in": {"A.0": 0}}},
            "C~1": {"0": {"val_in": {"A.0": 0}}},
            "B~2": {"0": {"val_in": {"A.0": 0}}},
        }
    )
