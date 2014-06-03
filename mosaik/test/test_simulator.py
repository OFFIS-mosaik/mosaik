from unittest import mock

import pytest

from mosaik import scenario, simulator, simmanager
from mosaik.test.util import SimMock


@pytest.yield_fixture
def world():
    world = scenario.World({})
    world.sims = {i: simmanager.LocalProcess(world, i, SimMock(), world.env,
                                             None)
                  for i in range(4)}
    world.df_graph.add_edges_from([(0, 2), (1, 2), (2, 3)],
                                  async_requests=False)
    world.df_graph[0][2]['wait_event'] = world.env.event()
    yield world
    world.shutdown()


def test_run():
    """Test if a process is started for every simulation."""
    def dummy_proc(world, sim, until):
        sim.proc_started = True
        yield world.env.event().succeed()

    class Sim:
        proc_started = False

        def stop(self):
            yield self.env.event().succeed()

    world = scenario.World({})
    Sim.env = world.env
    world.sims = {i: Sim() for i in range(2)}

    with mock.patch('mosaik.simulator.sim_process', dummy_proc):
        world.run(until=1)

    for sim in world.sims.values():
        assert sim.proc_started
    world.shutdown()


def test_sim_process():
    """``sim_process()`` is tested via test_mosaik.py."""
    assert True


def test_step_required(world):
    """Test *step_required is True*, becauce a simulator is waiting for us."""
    evt = simulator.step_required(world, world.sims[0])
    assert evt.triggered


def test_step_not_required(world):
    """Test *step_required is False*, because noone is waiting for us."""
    evt = simulator.step_required(world, world.sims[1])
    assert not evt.triggered

    evt = simulator.step_required(world, world.sims[2])
    assert not evt.triggered


def test_step_required_no_successors(world):
    """Test *step_required is True*, because there is noone that could be
    waiting for us."""
    evt = simulator.step_required(world, world.sims[3])
    assert evt.triggered


def test_wait_for_dependencies(world):
    """Test waiting for dependencies and triggering them."""
    for i in range(2):
        world.sims[i].step_required = world.env.event()
        if i == 0:
            world.sims[i].step_required.succeed()
    evt = simulator.wait_for_dependencies(world, world.sims[2])
    assert len(evt._events) == 2
    assert not evt.triggered
    for i in range(2):
        assert world.sims[i].step_required.triggered


def test_wait_for_dependencies_all_done(world):
    """All dependencies already stepped far enough. No waiting required."""
    world._df_cache = {0: {0: [], 1: []}}
    evt = simulator.wait_for_dependencies(world, world.sims[2])
    assert len(evt._events) == 0
    assert evt.triggered


def test_get_input_data(world):
    """Simple test for get_input_data()."""
    world._df_cache = {0: {
        0: {'1': {'x': 0, 'y': 1}},
        1: {'2': {'x': 2, 'z': 4}},
    }}
    world.sims[2].input_buffer = {'0': {'in': [5], 'spam': ['eggs']}}
    world.df_graph[0][2]['dataflows'] = [('1', '0', [('x', 'in')])]
    world.df_graph[1][2]['dataflows'] = [('2', '0', [('z', 'in')])]
    data = simulator.get_input_data(world, world.sims[2])
    assert data == {'0': {'in': [5, 0, 4], 'spam': ['eggs']}}


def test_step(world):
    inputs = object()
    sim = world.sims[0]
    assert (sim.last_step, sim.next_step) == (float('-inf'), 0)

    gen = simulator.step(world, sim, inputs)
    evt = next(gen)
    pytest.raises(StopIteration, gen.send, evt.value)
    assert evt.triggered
    assert (sim.last_step, sim.next_step) == (0, 1)


def test_get_outputs(world):
    world._df_cache[0] = {'spam': 'eggs'}
    world._df_cache[1] = {'foo': 'bar'}
    world._df_outattr[0][0] = ['x', 'y']
    wait_event = world.env.event()
    world.df_graph[0][2]['wait_event'] = wait_event
    world.sims[2].next_step = 2
    sim = world.sims[0]
    sim.last_step, sim.next_step = 0, 1

    gen = simulator.get_outputs(world, sim)
    evt = next(gen)
    pytest.raises(StopIteration, gen.send, evt.value)
    assert evt.triggered
    assert not wait_event.triggered
    assert 'wait_event' in world.df_graph[0][2]
    assert world._df_cache == {
        0: {'spam': 'eggs', 0: {'0': {'x': 0, 'y': 1}}},
        1: {'foo': 'bar'},
    }

    for s in world.sims.values():
        s.last_step, s.next_step = 1, 2
    sim.last_step, sim.next_step = 2, 3
    gen = simulator.get_outputs(world, sim)
    evt = next(gen)
    pytest.raises(StopIteration, gen.send, evt.value)
    assert evt.triggered
    assert wait_event.triggered
    assert 'wait_event' not in world.df_graph[0][2]
    assert world._df_cache == {
        2: {0: {'0': {'x': 0, 'y': 1}}},
    }


def test_get_progress():
    class Sim:
        def __init__(self, time):
            self.next_step = time

    sims = {i: Sim(0) for i in range(2)}
    assert simulator.get_progress(sims, 4) == 0

    sims[0].next_step = 1
    assert simulator.get_progress(sims, 4) == 12.5

    sims[0].next_step = 2
    assert simulator.get_progress(sims, 4) == 25

    sims[1].next_step = 3
    sims[0].next_step = 3
    assert simulator.get_progress(sims, 4) == 75

    sims[0].next_step = 4
    sims[1].next_step = 6
    assert simulator.get_progress(sims, 4) == 100
