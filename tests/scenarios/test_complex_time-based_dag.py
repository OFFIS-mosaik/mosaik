"""
Scenario 5

  A(1) ↘      ↗ C(1)
         B(2)
  D(4) ↗      ↘ E(3)
"""

from mosaik import World


def create_scenario(world: World):
    simulator_a = world.start("Remote", sim_id="A", step_size=1)
    simulator_b = world.start("Remote", sim_id="B", step_size=2)
    simulator_c = world.start("Remote", sim_id="C", step_size=1)
    simulator_d = world.start("Remote", sim_id="D", step_size=4)
    simulator_e = world.start("Remote", sim_id="E", step_size=3)
    model_a = simulator_a.A(init_val=0)
    model_b = simulator_b.B(init_val=0)
    model_c = simulator_c.B(init_val=0)
    model_d = simulator_d.B(init_val=0)
    model_e = simulator_e.B(init_val=0)
    world.connect(model_a, model_b, ("val_out", "val_in"))
    world.connect(model_d, model_b, ("val_out", "val_in"))
    world.connect(model_b, model_c, ("val_out", "val_in"))
    world.connect(model_b, model_e, ("val_out", "val_in"))


def test_scenario(world: World):
    create_scenario(world)
    world.run(until=5)

    world.assert_graph(
        """
        A~0 A~1
        A~0 B~0
        A~1 A~2
        A~2 A~3
        A~2 B~2
        A~3 A~4
        A~4 B~4
        B~0 B~2
        B~0 C~0
        B~0 C~1
        B~0 E~0
        B~2 B~4
        B~2 C~2
        B~2 C~3
        B~2 E~3
        B~4 C~4
        C~0 C~1
        C~1 C~2
        C~2 C~3
        C~3 C~4
        D~0 B~0
        D~0 B~2
        D~0 D~4
        D~4 B~4
        E~0 E~3
        """
    )

    world.assert_inputs(
        {
            "B~0": {"0.0": {"val_in": {"A.0.0": 1, "D.0.0": 0}}},
            "B~2": {"0.0": {"val_in": {"A.0.0": 3, "D.0.0": 0}}},
            "B~4": {"0.0": {"val_in": {"A.0.0": 5, "D.0.0": 0}}},
            "C~0": {"0.0": {"val_in": {"B.0.0": 1}}},
            "C~1": {"0.0": {"val_in": {"B.0.0": 1}}},
            "C~2": {"0.0": {"val_in": {"B.0.0": 3}}},
            "C~3": {"0.0": {"val_in": {"B.0.0": 3}}},
            "C~4": {"0.0": {"val_in": {"B.0.0": 5}}},
            "E~0": {"0.0": {"val_in": {"B.0.0": 1}}},
            "E~3": {"0.0": {"val_in": {"B.0.0": 3}}},
        }
    )
