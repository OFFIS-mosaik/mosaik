"""
C
  ↘
    B → D
  ↗
A
"""

from mosaik import World


def create_scenario(world: World):
    a = world.start("Generic", sim_id="A", step_type="time-based", step_size=1).A()
    b = world.start("Generic", sim_id="B", step_type="hybrid", trigger=["val_in"]).A()
    c = world.start("Generic", sim_id="C", step_type="time-based", step_size=1).A()
    d = world.start("Generic", sim_id="D", step_type="time-based", step_size=1).A()
    world.connect(c, b, ("val_out", "val_in"))
    world.connect(a, b, ("val_out", "val_in"))
    world.connect(b, d, ("val_out", "val_in"))


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
