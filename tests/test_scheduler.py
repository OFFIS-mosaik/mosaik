from mosaik import exceptions, scenario, scheduler, simmanager
import pytest

from tests.mocks.simulator_mock import SimulatorMock


# TODO: Create SimulatorMock for new API and paramterize world_fixture
@pytest.fixture(name='world')
def world_fixture():
    world = scenario.World({})
    world.sims = {
        i: simmanager.LocalProcess('', i, {'models': {}}, SimulatorMock(), world)
        for i in range(6)
    }
    world.df_graph.add_edges_from([(0, 2), (1, 2), (2, 3), (4, 5)],
                                  async_requests=False, pred_waiting=False,
                                  time_shifted=False, weak=False,
                                  trigger=False)
    world.df_graph.add_edges_from([(5, 4)],
                                  async_requests=False, pred_waiting=False,
                                  time_shifted=True, weak=False, trigger=False)
    world.cache_dependencies()
    world.df_graph[0][2]['wait_event'] = world.env.event()
    world.until = 4
    world.rt_factor = None
    yield world
    world.shutdown()


def test_run(monkeypatch):
    """Test if a process is started for every simulation."""
    world = scenario.World({})
    world.df_graph.add_nodes_from([0, 1])
    world.trigger_graph.add_node('dummy')

    def dummy_proc(world, sim, until, rt_factor, rt_strict, print_progress,
                   lazy_stepping):
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
        sid = 'dummy'
        next_steps = []

        def stop(self):
            yield world.env.event().succeed()

    Sim.env = world.env
    world.sims = {i: Sim() for i in range(2)}

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
    class DummyWorld:
        until = None
    pytest.raises(ValueError, next, scheduler.run(DummyWorld(), 10, -1))


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
                            scheduler.sim_process(None, Sim(), None, 1, False,
                                                  True, False))
    assert str(excinfo.value) == ('[Errno 1337] noob: Simulator "spam" closed '
                                  'its connection.')


@pytest.mark.parametrize('progress', [0, 2])
def test_has_next_step(world, progress, monkeypatch):
    """
    Test has_next_step without and with next_steps.
    """
    sim = world.sims[0]
    sim.progress = progress
    sim.next_steps = []

    def dummy_check(*args):
        pass

    monkeypatch.setattr(scheduler, 'check_and_resolve_deadlocks', dummy_check)

    gen = scheduler.has_next_step(world, sim)
    evt = next(gen)
    assert not evt.triggered

    sim.next_steps.append(1)
    with pytest.raises(StopIteration):
        next(gen)
    assert sim.next_step == max(1, progress)


@pytest.mark.parametrize("weak,number_waiting", [
    (True, 2),
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
    (-1, 1),
    (0, 0)
])
def test_wait_for_dependencies_shifted(world, progress, number_waiting):
    """
    Shifted dependency has not/has stepped far enough. Waiting is/is not required.
    """
    world.sims[5].progress = progress
    world.sims[4].next_step = 1
    evt = scheduler.wait_for_dependencies(world, world.sims[4], False)
    assert len(evt._events) == number_waiting
    assert evt.triggered == (not bool(number_waiting))


@pytest.mark.parametrize("lazy_stepping", [
    True,
    False
])
def test_wait_for_dependencies_lazy(world, lazy_stepping):
    """
    Test waiting for dependencies and triggering them.
    """
    world.sims[1].next_step = 1
    evt = scheduler.wait_for_dependencies(world, world.sims[1], lazy_stepping)
    assert len(evt._events) == 0
    assert evt.triggered == 1
    if lazy_stepping:
        assert 'wait_lazy' in world.df_graph[1][2]
        evt = scheduler.wait_for_dependencies(world, world.sims[1], True)
        assert len(evt._events) == 1
        assert evt.triggered == False


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
    world.df_graph[0][2]['cached_connections'] = [('1', '0', [('x', 'in')])]
    world.df_graph[1][2]['cached_connections'] = [('2', '0', [('z', 'in')])]
    data = scheduler.get_input_data(world, world.sims[2])
    assert data == {'0': {'in': {'0.1': 0, '1.2': 4, '3': 5},
                          'spam': {'3': 'eggs'}}}


def test_get_input_data_shifted(world):
    """
    Getting input data transmitted via a shifted connection.
    """
    world.sims[4].next_step = 0
    world._df_cache = {-1: {
        5: {'1': {'z': 7}}
    }}
    world.df_graph[5][4]['cached_connections'] = [('1', '0', [('z', 'in')])]
    data = scheduler.get_input_data(world, world.sims[4])
    assert data == {'0': {'in': {'5.1': 7}}}


def test_step(world):
    inputs = object()
    sim = world.sims[0]
    sim.meta['type'] = 'time-based'
    sim.meta['old-api'] = True
    sim.next_step = 0
    assert (sim.last_step, sim.next_step) == (-1, 0)

    gen = scheduler.step(world, sim, inputs, 0)
    evt = next(gen)
    pytest.raises(StopIteration, gen.send, evt.value)
    assert evt.triggered
    assert (sim.last_step, sim.progress_tmp) == (0, 0)


def test_get_outputs(world):
    world._df_cache[0] = {'spam': 'eggs'}
    world._df_cache[1] = {'foo': 'bar'}
    world._df_outattr[0][0] = ['x', 'y']
    wait_event = world.env.event()
    world.df_graph[0][2]['wait_event'] = wait_event
    world.sims[2].next_step = 2
    sim = world.sims[0]
    sim.meta['type'] = 'time-based'
    sim.progress = -1
    sim.last_step, sim.progress_tmp = 0, 0
    sim.idle_tmp = False

    gen = scheduler.get_outputs(world, sim)
    evt = next(gen)
    pytest.raises(StopIteration, gen.send, evt.value)
    scheduler.notify_dependencies(world, sim)
    scheduler.prune_dataflow_cache(world)
    assert sim.progress == 0
    assert evt.triggered
    assert not wait_event.triggered
    assert 'wait_event' in world.df_graph[0][2]
    assert world._df_cache == {
        0: {'spam': 'eggs', 0: {'0': {'x': 0, 'y': 1}}},
        1: {'foo': 'bar'},
    }

    for s in world.sims.values():
        s.last_step, s.next_step = 1, 2
    sim.progress = 1
    sim.last_step, sim.progress_tmp = 2, 2
    gen = scheduler.get_outputs(world, sim)
    evt = next(gen)
    pytest.raises(StopIteration, gen.send, evt.value)
    scheduler.notify_dependencies(world, sim)
    scheduler.prune_dataflow_cache(world)
    assert evt.triggered
    assert wait_event.triggered
    assert 'wait_event' not in world.df_graph[0][2]

    assert world._df_cache == {
        1: {'foo': 'bar'},
        2: {0: {'0': {'x': 0, 'y': 1}}},
    }


def test_get_outputs_shifted(world):
    world._df_cache[1] = {'spam': 'eggs'}
    world._df_outattr[5][0] = ['x', 'y']
    wait_event = world.env.event()
    world.df_graph[5][4]['wait_event'] = wait_event
    sim = world.sims[5]
    sim.meta['type'] = 'time-based'
    sim.progress = 0
    sim.last_step, sim.progress_tmp = 1, 1
    world.sims[4].next_step = 2

    gen = scheduler.get_outputs(world, sim)
    evt = next(gen)
    pytest.raises(StopIteration, gen.send, evt.value)
    scheduler.notify_dependencies(world, sim)
    scheduler.prune_dataflow_cache(world)
    assert evt.triggered
    assert wait_event.triggered
    assert 'wait_event' not in world.df_graph[5][4]
    assert world._df_cache == {
        1: {'spam': 'eggs', 5: {'0': {'x': 0, 'y': 1}}},
    }


def test_get_progress():
    class Sim:
        def __init__(self, time):
            self.progress = time

    sims = {i: Sim(-1) for i in range(2)}
    assert scheduler.get_progress(sims, 4) == 0

    sims[0].progress = 0
    assert scheduler.get_progress(sims, 4) == 12.5

    sims[0].progress = 1
    assert scheduler.get_progress(sims, 4) == 25

    sims[1].progress = 2
    sims[0].progress = 2
    assert scheduler.get_progress(sims, 4) == 75

    sims[0].progress = 3
    sims[1].progress = 5
    assert scheduler.get_progress(sims, 4) == 100
