"""Test that a scenario with a control loop in a group passes its
information on only after the same-time loop.
"""

from mosaik import World


def create_scenario(world: World):
    with world.group():
        a = world.start("LoopSim", sim_id="A", loop_length=2).A()
        b = world.start("LoopSim", sim_id="B", loop_length=2).A()
    c = world.start("Generic", sim_id="C").A()
    world.connect(a, b, ("loop_out", "loop_in"))
    world.connect(b, a, ("loop_out", "loop_in"), weak=True)
    world.connect(a, c, ("loop_out", "val_in"))


def test_scenario(world: World):
    create_scenario(world)
    world.run(until=1)

    world.assert_graph(
        """
        A~0:0 B~0:0
        B~0:0 A~0:1
        A~0:1 B~0:1
        B~0:1 A~0:2
        A~0:2 C~0
        """
    )

    world.assert_inputs(
        {
            "B~0:0": {"Loop": {"loop_in": {"A.Loop": 1}}},
            "A~0:1": {"Loop": {"loop_in": {"B.Loop": 1}}},
            "B~0:1": {"Loop": {"loop_in": {"A.Loop": 2}}},
            "A~0:2": {"Loop": {"loop_in": {"B.Loop": 2}}},
            "C~0": {"0": {"val_in": {"A.Loop": 2}}},
        }
    )
