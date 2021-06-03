from mosaik import exceptions, scenario, scheduler, simmanager
import pytest

from tests.mocks.simulator_mock import SimulatorMock


@pytest.fixture(name='world')
def world_fixture(request):
    if request.param == 'time-based':
        time_shifted = True
        weak = False
        trigger = False
    else:
        time_shifted = False
        weak = True
        trigger = True
    world = scenario.World({})
    world.sims = {i: simmanager.LocalProcess('', i,
        {'models': {}, 'type': request.param}, SimulatorMock(request.param),
        world) for i in range(6)}
    world.df_graph.add_edges_from([(0, 2), (1, 2), (2, 3), (4, 5)],
                                  async_requests=False, pred_waiting=False,
                                  time_shifted=False, weak=False,
                                  trigger=trigger)
    world.df_graph.add_edges_from([(5, 4)], async_requests=False,
                                  pred_waiting=False,
                                  time_shifted=time_shifted, weak=weak,
                                  trigger=trigger)
    world.cache_dependencies()
    world.cache_related_sims()
    world.df_graph[0][2]['wait_event'] = world.env.event()
    world.until = 4
    world.rt_factor = None
    if request.param == 'time-based':
        world.trigger_graph.add_nodes_from(range(6))
    else:
        world.trigger_graph = world.df_graph
    world.cache_triggering_ancestors()
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


@pytest.mark.parametrize('world', ['time-based', 'event-based'], indirect=True)
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


@pytest.mark.parametrize('world', ['time-based', 'event-based'], indirect=True)
@pytest.mark.parametrize("weak,number_waiting", [(True, 2), (False, 2)])
def test_wait_for_dependencies(world, weak, number_waiting):
    """
    Test waiting for dependencies and triggering them.
    """
    world.sims[2].next_step = 0
    world.df_graph[1][2]['weak'] = weak
    evt = scheduler.wait_for_dependencies(world, world.sims[2], True)
    assert len(evt._events) == number_waiting
    assert not evt.triggered


@pytest.mark.parametrize('world', ['time-based'], indirect=True)
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


@pytest.mark.parametrize('world', ['time-based'], indirect=True)
@pytest.mark.parametrize("progress,number_waiting", [(-1, 1), (0, 0)])
def test_wait_for_dependencies_shifted(world, progress, number_waiting):
    """
    Shifted dependency has not/has stepped far enough. Waiting is/is not
    required.
    """
    world.sims[5].progress = progress
    world.sims[4].next_step = 1
    evt = scheduler.wait_for_dependencies(world, world.sims[4], False)
    assert len(evt._events) == number_waiting
    assert evt.triggered == (not bool(number_waiting))


@pytest.mark.parametrize('world', ['time-based'], indirect=True)
@pytest.mark.parametrize("lazy_stepping", [True, False])
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


@pytest.mark.parametrize('world', ['time-based'], indirect=True)
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


@pytest.mark.parametrize('world', ['time-based'], indirect=True)
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


@pytest.mark.parametrize('world,next_steps,next_step_s1,expected',
                         [('time-based', [], 2, 5), ('time-based', [4], 2, 3),
                             ('event-based', [3], None, 2),
                             ('event-based', [3], 2, 1)], indirect=['world'])
def test_get_max_advance(world, next_steps, next_step_s1, expected):
    sim = world.sims[2]
    sim.next_step = 1
    sim.next_steps = next_steps

    # In the event-based world, sims 0 and 1 are triggering ancestors of sim 2:
    world.sims[0].next_steps = [3]
    world.sims[1].next_step = next_step_s1

    max_advance = scheduler.get_max_advance(world, sim, until=5)
    assert max_advance == expected


# TODO: Implement test/parameter for new API (passing max_advance)
@pytest.mark.parametrize('world', ['time-based', 'event-based'], indirect=True)
def test_step(world):
    inputs = object()
    sim = world.sims[0]
    sim.meta['old-api'] = True
    sim.next_step = 0
    assert (sim.last_step, sim.next_step) == (-1, 0)

    gen = scheduler.step(world, sim, inputs, 0)
    evt = next(gen)
    pytest.raises(StopIteration, gen.send, evt.value)
    assert evt.triggered
    assert (sim.last_step, sim.progress_tmp) == (0, 0)


# TODO: Test also for output_time if 'time' is indicated by event-based sims
@pytest.mark.parametrize('world, cache_t1',
                         [('time-based', True),
                          ('event-based', False)], indirect=['world'])
def test_get_outputs(world, cache_t1):
    world._df_cache[0] = {'spam': 'eggs'}
    world._df_outattr[0][0] = ['x', 'y']
    world.df_graph[0][2]['dataflows'] = [('1', '0', [('x', 'in')])]
    sim = world.sims[0]
    sim.last_step, sim.progress_tmp = 0, 1
    sim.output_time = -1

    gen = scheduler.get_outputs(world, sim)
    evt = next(gen)
    pytest.raises(StopIteration, gen.send, evt.value)
    assert evt.triggered

    expected_cache = {0: {0: {'0': {'x': 0, 'y': 1}}, 'spam': 'eggs'}}
    if cache_t1:
        expected_cache[1] = {0: {'0': {'x': 0, 'y': 1}}}

    assert world._df_cache == expected_cache

    assert sim.output_time == 0


@pytest.mark.parametrize('world', ['event-based'], indirect=True)
def test_get_outputs_buffered(world):
    sim = world.sims[0]
    sim.last_step = 0
    world._df_outattr[0][0] = ['x', 'y', 'z']
    sim.buffered_output.setdefault(('0', 'x'), []).append((2, '0', 'in'))
    sim.buffered_output = {
        ('0', 'x'): [(2, '0', 'in')],
        ('0', 'z'): [(1, '0', 'in')],
    }

    gen = scheduler.get_outputs(world, sim)
    evt = next(gen)
    pytest.raises(StopIteration, gen.send, evt.value)
    assert evt.triggered

    assert world.sims[2].timed_input_buffer.input_queue == [
        (0, 0, '0.0', '0', 'in', 0)]
    assert world.sims[1].timed_input_buffer.input_queue == []


@pytest.mark.parametrize('world', ['event-based'], indirect=True)
@pytest.mark.parametrize("count", [
    0,
    pytest.param(100, marks=pytest.mark.xfail(raises=exceptions.SimulationError))])
def test_treat_cycling_output(world, count):
    """
    Tests if progress_tmp is adjusted when a triggering cycle could cause
    an earlier step than predicted by get_max_advance function, or if an error
    is risen if the maximum iteration count is reached.
    """
    sim = world.sims[4]

    for src, dest in [(4, 5), (5, 4)]:
        world.df_graph[src][dest]['dataflows'] = [('1', '0', [('x', 'in')])]
        world.entity_graph.add_node(f'{dest}.0', sim=None, type='dummy_type')
        world.sims[dest].meta['models'] = {'dummy_type': {'trigger': ['in']}}
    world.cache_trigger_cycles()

    sim.trigger_cycles[0]['time'] = 1
    sim.trigger_cycles[0]['count'] = count

    sim.last_step = output_time = 1
    sim.progress_tmp = 1
    data = {'1': {'x': 1}}
    scheduler.treat_cycling_output(world, sim, data, output_time)
    assert sim.progress_tmp == 0


@pytest.mark.parametrize('world', ['event-based'], indirect=True)
@pytest.mark.parametrize('output_time, next_steps', [(1, [2]), (2, []), (3, [3])])
@pytest.mark.parametrize('progress, pop_wait', [(1, False), (2, True)])
def test_notify_dependencies(world, output_time, next_steps, progress, pop_wait):
    sim = world.sims[0]
    sim.progress = -1
    sim.progress_tmp = progress

    wait_event = world.env.event()
    world.df_graph[0][2]['wait_event'] = wait_event
    world.df_graph[0][2]['dataflows'] = [('1', '0', [('x', 'in')])]
    sim.data = {'1': {'x': 1}}
    sim.output_time = output_time

    world.sims[2].next_step = 2
    world.sims[2].has_next_step = world.env.event().succeed()

    scheduler.notify_dependencies(world, sim)

    assert sim.progress == sim.progress_tmp
    assert world.sims[2].next_steps == next_steps


@pytest.mark.parametrize('world', ['event-based'], indirect=True)
def test_notify_dependencies_trigger(world):
    sim = world.sims[0]
    sim.progress = -1
    sim.progress_tmp = 1

    world.df_graph[0][2].pop('wait_event')
    world.df_graph[0][2]['dataflows'] = [('1', '0', [('x', 'in')])]
    sim.data = {'1': {'x': 1}}
    sim.output_time = 1

    world.sims[2].next_step = None
    world.sims[2].has_next_step = world.env.event()

    scheduler.notify_dependencies(world, sim)

    assert world.sims[2].next_steps == [1]
    assert world.sims[2].has_next_step.triggered


@pytest.mark.parametrize('world', ['time-based'], indirect=True)
def test_prune_dataflow_cache(world):
    world._df_cache[0] = {'spam': 'eggs'}
    world._df_cache[1] = {'foo': 'bar'}
    for s in world.sims.values():
        s.last_step = 1
    scheduler.prune_dataflow_cache(world)

    assert world._df_cache == {
        1: {'foo': 'bar'},
    }


@pytest.mark.parametrize('world', ['time-based'], indirect=True)
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
