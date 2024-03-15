"""
Scenario 22:

"""

import pytest
from mosaik import World


@pytest.mark.weak
def create_scenario(world: World):
    with world.group():
        a = world.start("LoopSim", sim_id="Loop", loop_length=2).A()
        b = world.start("EchoSim", sim_id="Echo").A()

    world.set_initial_event(a.sid)

    world.connect(a, b, ("loop_out", "loop_in"))
    world.connect(b, a, ("loop_out", "loop_in"), weak=True)


def test_scenario(world: World):
    create_scenario(world)
    world.run(until=2)

    world.assert_graph(
        """
        Loop~0:0 Echo~0:0
        Echo~0:0 Loop~0:1
        Loop~0:1 Echo~0:1
        Echo~0:1 Loop~0:2
        Loop~0:2 Loop~1:0
        Loop~1:0 Echo~1:0
        Echo~1:0 Loop~1:1
        Loop~1:1 Echo~1:1
        Echo~1:1 Loop~1:2
        """
    )

    world.assert_inputs(
        {
            "Echo~0:0": {"Echo": {"loop_in": {"Loop.Loop": 1}}},
            "Loop~0:1": {"Loop": {"loop_in": {"Echo.Echo": 1}}},
            "Echo~0:1": {"Echo": {"loop_in": {"Loop.Loop": 2}}},
            "Loop~0:2": {"Loop": {"loop_in": {"Echo.Echo": 2}}},
            "Echo~1:0": {"Echo": {"loop_in": {"Loop.Loop": 1}}},
            "Loop~1:1": {"Loop": {"loop_in": {"Echo.Echo": 1}}},
            "Echo~1:1": {"Echo": {"loop_in": {"Loop.Loop": 2}}},
            "Loop~1:2": {"Loop": {"loop_in": {"Echo.Echo": 2}}},
        }
    )
