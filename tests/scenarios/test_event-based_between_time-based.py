"""
Scenario 30::
C
  ↘
    B → D
  ↗
A
"""

from mosaik import World


def create_scenario(world: World):
    model_a = world.start(
        "Generic", sim_id="A", step_type="time-based", step_size=1
    ).A()
    model_b = world.start("Generic", sim_id="B", step_type="event-based").A()
    model_c = world.start(
        "Generic", sim_id="C", step_type="time-based", step_size=1
    ).A()
    model_d = world.start(
        "Generic", sim_id="D", step_type="time-based", step_size=1
    ).A()
    world.connect(model_c, model_b, ("val_out", "val_in"))
    world.connect(model_a, model_b, ("val_out", "val_in"))
    world.connect(model_b, model_d, ("val_out", "val_in"))


def test_scenario(world: World):
    create_scenario(world)
    world.run(until=2)

    world.assert_graph(
        """
        A~0 B~0
        C~0 B~0
        B~0 D~0
        A~0 A~1
        C~0 C~1
        D~0 D~1
        A~1 B~1
        C~1 B~1
        B~1 D~1
        """
    )

    world.assert_inputs(
        {
            "B~0": {"0": {"val_in": {"A.0": 0, "C.0": 0}}},
            "D~0": {"0": {"val_in": {"B.0": 0}}},
            "B~1": {"0": {"val_in": {"A.0": 1, "C.0": 1}}},
            "D~1": {"0": {"val_in": {"B.0": 1}}},
        }
    )
