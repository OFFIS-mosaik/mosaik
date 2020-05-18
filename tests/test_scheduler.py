from mosaik import exceptions, scenario, scheduler, simmanager
from mosaik.input_messages import InputMessages
import pytest

from tests.mocks.simulator_mock import SimulatorMock
from tests.mocks.simulator_mock_nonextstep import SimulatorMockNonextstep


@pytest.fixture(name='world')
def world_fixture():
    world = scenario.World({})
    world.sims = {
        i: simmanager.LocalProcess('', i, {'models': {}}, SimulatorMock(), world)
        for i in range(7)
    }
    world.sims[7] = simmanager.LocalProcess('', 7, {'models': {}}, SimulatorMockNonextstep(), world)
    world.df_graph.add_edges_from([(0, 2), (1, 2), (2, 3), (4, 5), (6, 7)],
                                  async_requests=False, weak=False)
    world.shifted_graph.add_nodes_from([0, 1, 2, 3, 4, 5, 6, 7])
    world.shifted_graph.add_edges_from([(5, 4)])
    world.df_graph[0][2]['wait_event'] = world.env.event()
    yield world
    world.shutdown()


def test_run(monkeypatch):
    """Test if a process is started for every simulation."""
    world = scenario.World({})

    def dummy_proc(world, sim, until, rt_factor, rt_strict, lazy_stepping):
        sim.proc_started = True
        yield world.env.event().succeed()

    class Sim:
        class proxy:
            @classmethod
            def setup_done(cls):
                return world.env.event().succeed()

        proc_started = False
        meta = {
            'api_version': (2, 2),
        }

        def stop(self):
            yield self.env.event().succeed()

    Sim.env = world.env
    world.sims = {i: Sim() for i in range(2)}
    for sim_id in world.sims:
        world.df_graph.add_node(sim_id)
        world.shifted_graph.add_node(sim_id)

    monkeypatch.setattr(scheduler, 'sim_process', dummy_proc)
    try:
        world.run(until=1)
    except:
        world.shutdown()
        raise
    else:
        for sim in world.sims.values():
            assert sim.proc_started


def test_run_illegal_rt_factor():
    pytest.raises(ValueError, next, scheduler.run(None, 10, -1))


def test_sim_process():
    """
    ``sim_process()`` is tested via test_mosaik.py.
    """
    assert True


def test_sim_process_error(monkeypatch):
    class Sim:
        sid = 'spam'

    def get_keep_running_func(world, sim, until, rt_factor, rt_start):
        raise ConnectionError(1337, 'noob')

    monkeypatch.setattr(scheduler, 'get_keep_running_func',
                        get_keep_running_func)

    excinfo = pytest.raises(exceptions.SimulationError, next,
                            scheduler.sim_process(None, Sim(), None, 1, False, True))
    assert str(excinfo.value) == ('[Errno 1337] noob: Simulator "spam" closed '
                                  'its connection.')


@pytest.mark.parametrize('progress,self_step,input_step,expected',
                         [(0, 0, 1, 0),
                          (2, 2, 1, 2),
                          (1, None, None, None)])
def test_get_next_step(world, progress, self_step, input_step, expected):
    """
    Test get_next_step.
    """
    sim = world.sims[7]
    sim.progress = progress
    sim.next_self_step = self_step
    if input_step is not None:
        sim.input_messages = InputMessages()
        sim.input_messages.add_empty_time(input_step)
    assert scheduler.get_next_step(sim) == expected


def test_has_next_step_selfstep(world):
    """
    Test has_next_step when there's a self-step.
    """
    sim = world.sims[0]
    sim.next_self_step = 1

    gen = scheduler.has_next_step(world, sim)
    evt = next(gen)
    pytest.raises(StopIteration, gen.send, evt.value)
    assert evt.triggered
    assert sim.next_step == 1


@pytest.mark.parametrize('progress', [0, 2])
def test_has_next_step_noselfstep(world, progress):
    """
    Test has_next_step when there's no self-step.
    """
    sim = world.sims[0]
    sim.progress = progress
    sim.next_self_step = None
    assert sim.next_step is None

    gen = scheduler.has_next_step(world, sim)
    evt = next(gen)
    assert not evt.triggered

    sim.input_messages = InputMessages()
    sim.input_messages.add_empty_time(1)
    with pytest.raises(StopIteration):
        next(gen)
    assert sim.next_step == max(1, progress)


@pytest.mark.parametrize("weak,number_waiting", [
    (True, 1),
    (False, 2)
])
def test_wait_for_dependencies(world, weak, number_waiting):
    """
    Test waiting for dependencies and triggering them.
    """
    world.sims[2].next_step = 0
    world.df_graph[1][2]['weak'] = weak
    evt = scheduler.wait_for_dependencies(world, world.sims[2], True)
    assert len(evt._events) == number_waiting
    assert not evt.triggered


def test_wait_for_dependencies_all_done(world):
    """
    All dependencies already stepped far enough. No waiting required.
    """
    world.sims[2].next_step = 0
    for dep_sid in [0, 1]:
        world.sims[dep_sid].progress = 1
    evt = scheduler.wait_for_dependencies(world, world.sims[2], True)
    assert len(evt._events) == 0
    assert evt.triggered


@pytest.mark.parametrize("progress,number_waiting", [
    (0, 1),
    (1, 0)
])
def test_wait_for_dependencies_shifted(world, progress, number_waiting):
    """
    Shifted dependency has not/has stepped far enough. Waiting is/is not required.
    """
    world.sims[5].progress = progress
    print(world.sims[5].progress)
    world.sims[4].next_step = 1
    evt = scheduler.wait_for_dependencies(world, world.sims[4], False)
    assert len(evt._events) == number_waiting
    assert evt.triggered == (not bool(number_waiting))


@pytest.mark.parametrize("lazy_stepping,number_waiting", [
    (True, 1),
    (False, 0)
])
def test_wait_for_dependencies_lazy(world, lazy_stepping, number_waiting):
    """
    Test waiting for dependencies and triggering them.
    """
    world.sims[1].next_step = 1
    evt = scheduler.wait_for_dependencies(world, world.sims[1], lazy_stepping)
    assert len(evt._events) == number_waiting
    assert evt.triggered == (not bool(number_waiting))


def test_get_input_data(world):
    """
    Simple test for get_input_data().
    """
    world.sims[2].next_step = 0
    world._df_cache = {0: {
        0: {'1': {'x': 0, 'y': 1}},
        1: {'2': {'x': 2, 'z': 4}},
    }}
    world.sims[2].input_buffer = {'0': {'in': {'3': 5}, 'spam': {'3': 'eggs'}}}
    world.df_graph[0][2]['dataflows'] = [('1', '0', [('x', 'in')])]
    world.df_graph[1][2]['dataflows'] = [('2', '0', [('z', 'in')])]
    world.df_graph[0][2]['messageflows'] = [('0', '0', [('y', 'in')])]
    world.df_graph[1][2]['messageflows'] = []
    world.sims[2].input_messages = InputMessages()
    world.sims[2].input_messages.set_connections(
        [world.df_graph, world.shifted_graph], 2)
    print(world.sims[2].input_messages.predecessors)
    world.sims[2].input_messages.add(0, 0, '0', 'y', 3)
    data = scheduler.get_input_data(world, world.sims[2])
    assert data == {'0': {'in': {'0.0.y': [3], '0.1': 0, '1.2': 4, '3': 5},
                          'spam': {'3': 'eggs'}}}


def test_get_input_data_shifted(world):
    """
    Getting input data transmitted via a shifted connection.
    """
    world._df_cache = {-1: {
        5: {'1': {'z': 7}}
    }}
    world.sims[4].next_step = 0
    world.shifted_graph[5][4]['dataflows'] = [('1', '0', [('z', 'in')])]
    data = scheduler.get_input_data(world, world.sims[4])
    assert data == {'0': {'in': {'5.1': 7}}}


def test_step(world):
    inputs = object()
    sim = world.sims[0]
    sim.next_step = 0
    assert (sim.last_step, sim.progress_tmp, sim.next_self_step, sim.next_step) == (-1, 0, None, 0)

    gen = scheduler.step(world, sim, inputs)
    evt = next(gen)
    pytest.raises(StopIteration, gen.send, evt.value)
    assert evt.triggered
    assert (sim.last_step, sim.progress_tmp, sim.next_self_step, sim.next_step) == (0, 1, 1, None)


def test_step_nonextstep(world):
    inputs = object()
    sim = world.sims[7]
    sim.next_step = 0
    assert (sim.last_step, sim.progress_tmp, sim.next_self_step, sim.next_step) == (-1, 0, None, 0)
    world.sims[6].progress = 2

    gen = scheduler.step(world, sim, inputs)
    evt = next(gen)
    pytest.raises(StopIteration, gen.send, evt.value)
    assert evt.triggered
    assert (sim.last_step, sim.progress_tmp, sim.next_self_step, sim.next_step) == (0, 2, None, None)


def test_get_outputs(world):
    world._df_cache[0] = {'spam': 'eggs'}
    world._df_cache[1] = {'foo': 'bar'}
    world._df_outattr[0][0] = ['x', 'y']
    wait_event = world.env.event()
    world.df_graph[0][2]['wait_event'] = wait_event
    world.df_graph[0][2]['messageflows'] = [('0', '0', [('y', 'in'), ('z', 'in')])]
    world.df_graph[1][2]['messageflows'] = []
    world.sims[2].next_step = 2
    world.sims[2].input_messages = InputMessages()
    world.sims[2].input_messages.set_connections([world.df_graph, world.shifted_graph], 2)
    world.sims[2].has_next_step = world.env.event()
    sim = world.sims[0]
    sim.last_step, sim.progress_tmp, sim.next_step = 0, 1, 1

    gen = scheduler.get_outputs(world, sim)
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
        s.last_step, s.progress, s.next_step = 1, 2, 2
    sim.last_step, sim.progress_tmp, sim.next_step = 2, 3, 3
    gen = scheduler.get_outputs(world, sim)
    evt = next(gen)
    pytest.raises(StopIteration, gen.send, evt.value)
    assert evt.triggered
    assert wait_event.triggered
    assert 'wait_event' not in world.df_graph[0][2]
    assert world._df_cache == {
        1: {'foo': 'bar'},
        2: {0: {'0': {'x': 0, 'y': 1}}},
    }
    assert dict(world.sims[2].input_messages.predecessors[(0, '0', 'y')][
                    'input_queue']) == {0: 1, 2: 1}
    assert dict(world.sims[2].input_messages.predecessors[(0, '0', 'z')][
                    'input_queue']) == {}
    assert sim.progress == 3


def test_get_outputs_shifted(world):
    world._df_cache[1] = {'spam': 'eggs'}
    world._df_outattr[5][0] = ['x', 'y']
    world.shifted_graph[5][4]['messageflows'] = [('0', '0', [('y', 'in'),])]
    wait_event = world.env.event()
    world.shifted_graph[5][4]['wait_shifted'] = wait_event
    sim = world.sims[5]
    sim.last_step, sim.progress_tmp, sim.next_step = 1, 2, 2
    world.sims[4].next_step = 2
    world.sims[4].input_messages = InputMessages()
    world.sims[4].input_messages.set_connections(
        [world.df_graph, world.shifted_graph], 4)
    world.sims[4].has_next_step = world.env.event()

    gen = scheduler.get_outputs(world, sim)
    evt = next(gen)
    pytest.raises(StopIteration, gen.send, evt.value)
    assert evt.triggered
    assert wait_event.triggered
    assert 'wait_shifted' not in world.shifted_graph[5][4]
    assert world._df_cache == {
        1: {'spam': 'eggs', 5: {'0': {'x': 0, 'y': 1}}},
    }
    assert dict(world.sims[4].input_messages.predecessors[(5, '0', 'y')][
                    'input_queue']) == {2: 1}


def test_get_progress():
    class Sim:
        def __init__(self, time):
            self.progress = time

    sims = {i: Sim(0) for i in range(2)}
    assert scheduler.get_progress(sims, 4) == 0

    sims[0].progress = 1
    assert scheduler.get_progress(sims, 4) == 12.5

    sims[0].progress = 2
    assert scheduler.get_progress(sims, 4) == 25

    sims[1].progress = 3
    sims[0].progress = 3
    assert scheduler.get_progress(sims, 4) == 75

    sims[0].progress = 4
    sims[1].progress = 6
    assert scheduler.get_progress(sims, 4) == 100
