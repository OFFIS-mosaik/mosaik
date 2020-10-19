from mosaik import exceptions, scenario, scheduler, simmanager
import pytest

from tests.mocks.simulator_mock import SimulatorMock


@pytest.fixture(name='world')
def world_fixture():
    world = scenario.World({})
    world.sims = {
        i: simmanager.LocalProcess('', i, {'models': {}}, SimulatorMock(), world)
        for i in range(6)
    }
    world.df_graph.add_edges_from([(0, 2), (1, 2), (2, 3), (4, 5)],
                    async_requests=False, time_shifted=False, trigger=False)
    world.df_graph.add_edges_from([(5, 4)],
                    async_requests=False, time_shifted=True, trigger=False)
    world.df_graph[0][2]['wait_event'] = world.env.event()
    yield world
    world.shutdown()


def test_run(monkeypatch):
    """Test if a process is started for every simulation."""
    world = scenario.World({})

    def dummy_proc(world, sim, until, rt_factor, rt_strict, print_progress):
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
    pytest.raises(ValueError, next, scheduler.run(None, 10, -1))


def test_sim_process():
    """
    ``sim_process()`` is tested via test_mosaik.py.
    """
    assert True


def test_sim_process_error(monkeypatch):
    class Sim:
        sid = 'spam'

    def get_keep_running_func(world, sim, until):
        raise ConnectionError(1337, 'noob')

    monkeypatch.setattr(scheduler, 'get_keep_running_func',
                        get_keep_running_func)

    excinfo = pytest.raises(exceptions.SimulationError, next,
                            scheduler.sim_process(None, Sim(), None, 1, False, True))
    assert str(excinfo.value) == ('[Errno 1337] noob: Simulator "spam" closed '
                                  'its connection.')


def test_wait_for_dependencies(world):
    """
    Test waiting for dependencies and triggering them.
    """
    world.sims[2].next_step = 0
    evt = scheduler.wait_for_dependencies(world, world.sims[2])
    assert len(evt._events) == 2
    assert not evt.triggered


def test_wait_for_dependencies_all_done(world):
    """
    All dependencies already stepped far enough. No waiting required.
    """
    world.sims[2].next_step = 0
    for dep_sid in [0, 1]:
        world.sims[dep_sid].progress = 1

    evt = scheduler.wait_for_dependencies(world, world.sims[2])
    assert len(evt._events) == 0
    assert evt.triggered


def test_wait_for_dependencies_shifted(world):
    """
    Shifted dependency has not yet stepped far enough. Waiting is required.
    """
    world.sims[5].progress = -1
    world.sims[4].next_step = 1
    world.sims[5].step_required = world.env.event()
    evt = scheduler.wait_for_dependencies(world, world.sims[4])
    assert len(evt._events) == 2
    assert not evt.triggered


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
    world.df_graph[5][4]['dataflows'] = [('1', '0', [('z', 'in')])]
    data = scheduler.get_input_data(world, world.sims[4])
    assert data == {'0': {'in': {'5.1': 7}}}


def test_step(world):
    inputs = object()
    sim = world.sims[0]
    sim.meta['type'] = 'discrete-time'
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
    sim.meta['type'] = 'discrete-time'
    sim.progress = -1
    sim.last_step, sim.progress_tmp = 0, 0

    gen = scheduler.get_outputs(world, sim, empty_step=False)
    evt = next(gen)
    pytest.raises(StopIteration, gen.send, evt.value)
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
    gen = scheduler.get_outputs(world, sim, empty_step=False)
    evt = next(gen)
    pytest.raises(StopIteration, gen.send, evt.value)
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
    sim.meta['type'] = 'discrete-time'
    sim.progress = 0
    sim.last_step, sim.progress_tmp = 1, 1
    world.sims[4].next_step = 2

    gen = scheduler.get_outputs(world, sim, empty_step=False)
    evt = next(gen)
    pytest.raises(StopIteration, gen.send, evt.value)
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
