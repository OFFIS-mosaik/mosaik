import pytest

from mosaik import World
from mosaik.starters import PythonStarter
from tests.simulators.blocking_sim import BlockingSim


def create_scenario(world: World):
    with world.group():
        blocking = world.start(PythonStarter(BlockingSim), "Blocker").Entity()
        generic = world.start(
            "Generic",
            sim_id="Generic",
            step_type="event-based",
            output_timing={0: [0, 1]},
        ).A()
        world.set_initial_event(generic.sid)
        world.connect(blocking, generic, ("out", "val_in"), weak=True)
        world.connect(generic, blocking, ("val_out", "in"), weak=True)


@pytest.mark.xfail(reason="should trigger cannot progress backwards")
def test_scenario(world: World):
    create_scenario(world)
    world.run(until=2)
