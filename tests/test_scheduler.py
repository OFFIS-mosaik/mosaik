import asyncio
from heapq import heappush
import pytest
from tqdm import tqdm
from typing import Iterable

from mosaik import exceptions, scenario, scheduler, simmanager
from mosaik.adapters import V3ToV2Adapter, init_and_get_adapter
from mosaik.proxies import LocalProxy

from tests.mocks.simulator_mock import SimulatorMock


async def does_coroutine_stall(coro):
    """
    Executes the given coroutine until it first passes control back to
    the event loop (or until it's done otherwise). Returns whether
    control is ever passed back to the event loop.
    """
    task = asyncio.create_task(coro)
    async def canceller():
        if not task.done():
            task.cancel()
    await asyncio.gather(task, canceller(), return_exceptions=True)
    return task.cancelled()


@pytest.fixture(name='world')
def world_fixture(request):
    if request.param == 'time-based':
        time_shifted = True
        weak = False
        trigger = set()
    else:
        time_shifted = False
        weak = True
        trigger = set([('1', 'x')]) # TODO: Is this correct?
    world = scenario.World({})
    for i in range(6):
        proxy = LocalProxy(SimulatorMock(request.param), simmanager.MosaikRemote(world, i))
        proxy = world.loop.run_until_complete(init_and_get_adapter(proxy, i, {"time_resolution": 1.0}))
        world.sims[i] = simmanager.SimRunner(
                i,
                proxy,
            )
    class DummyTask:
        def done(self):
            return False
    for sim in world.sims.values():
        sim.task = DummyTask()
    for src, dest in [(0, 2), (1, 2), (2, 3), (4, 5)]:
        world.df_graph.add_edge(
            src,
            dest,
            async_requests=False,
            pred_waiting=False,
            time_shifted=False,
            weak=False,
            trigger=trigger,
            cached_connections=[],
        )
    world.df_graph.add_edge(
        5,
        4,
        async_requests=False,
        pred_waiting=False,
        time_shifted=time_shifted,
        weak=weak,
        trigger=trigger,
        cached_connections=[],
    )
    world.cache_dependencies()
    world.cache_related_sims()
    world.sims[0].successors[world.sims[2]].wait_data.clear()
    world.until = 4
    world.rt_factor = None
    world.cache_triggering_ancestors()
    yield world
    world.shutdown()


def test_run(monkeypatch):
    """Test if a process is started for every simulation."""
    world = scenario.World({})
    world.df_graph.add_nodes_from([0, 1], trigger=True)

    async def dummy_proc(world, sim, until, rt_factor, rt_strict, lazy_stepping):
        sim.proc_started = True

    class proxy:
        @classmethod
        async def send(cls, *args, **kwargs):
            return None

        @classmethod
        async def stop(cls):
            return None

        meta = {
            'api_version': '2.2',
            'type': 'time-based'
        }
        
    world.sims = {i: simmanager.SimRunner(i, proxy) for i in range(2)}

    monkeypatch.setattr(scheduler, 'sim_process', dummy_proc)
    try:
        world.run(until=1)
    except:
        world.shutdown()
        raise
    else:
        for sim in world.sims.values():
            assert sim.proc_started


@pytest.mark.asyncio
async def test_run_illegal_rt_factor():
    class DummyWorld:
        until = None
    with pytest.raises(ValueError):
        await scheduler.run(DummyWorld(), 10, -1)


def test_sim_process():
    """
    ``sim_process()`` is tested via test_mosaik.py.
    """
    assert True


@pytest.mark.asyncio
async def test_sim_process_error(monkeypatch):
    class Sim:
        sid = 'spam'

    def get_keep_running_func(world, sim, until, rt_factor, rt_start):
        raise ConnectionError(1337, 'noob')

    monkeypatch.setattr(scheduler, 'get_keep_running_func',
                        get_keep_running_func)

    with pytest.raises(exceptions.SimulationError) as excinfo:
        await scheduler.sim_process(None, Sim(), None, 1, False, False)
    assert str(excinfo.value) == ('[Errno 1337] noob: Simulator "spam" closed '
                                  'its connection.')


@pytest.mark.asyncio
@pytest.mark.parametrize('world', ['time-based', 'event-based'], indirect=True)
@pytest.mark.parametrize('next_steps_empty', [True, False])
async def test_has_next_step(world, next_steps_empty, monkeypatch):
    """
    Test has_next_step without and with next_steps.
    """
    sim = world.sims[0]
    sim.next_steps = ([] if next_steps_empty else [1])
    sim.tqdm = tqdm(disable=True)

    def dummy_check(*args):
        pass

    monkeypatch.setattr(scheduler, 'check_and_resolve_deadlocks', dummy_check)

    stalled = await does_coroutine_stall(scheduler.wait_for_next_step(world, sim))
    assert stalled == next_steps_empty
    assert sim.has_next_step.is_set() == (not next_steps_empty)


def any_unset(events: Iterable[asyncio.Event]) -> bool:
    """
    Returns whether any of the events of the given iterable is unset.
    """
    return any(not e.is_set() for e in events)


@pytest.mark.asyncio
@pytest.mark.parametrize('world', ['time-based', 'event-based'], indirect=True)
@pytest.mark.parametrize("weak,number_waiting", [(True, 2), (False, 2)])
async def test_wait_for_dependencies(world, weak, number_waiting):
    """
    Test waiting for dependencies and triggering them.
    """
    test_sim = world.sims[2]
    heappush(test_sim.next_steps, 0)
    world.df_graph[1][2]['weak'] = weak
    stalled = await does_coroutine_stall(
        scheduler.wait_for_dependencies(world, test_sim, True)
    )
    assert len(test_sim.wait_events) == number_waiting
    assert stalled


@pytest.mark.asyncio
@pytest.mark.parametrize('world', ['time-based'], indirect=True)
async def test_wait_for_dependencies_all_done(world):
    """
    All dependencies already stepped far enough. No waiting required.
    """
    heappush(world.sims[2].next_steps, 0)
    for dep_sid in [0, 1]:
        world.sims[dep_sid].progress = 1
    stalled = await does_coroutine_stall(
        scheduler.wait_for_dependencies(world, world.sims[2], True)
    )
    assert not stalled
    assert len(world.sims[2].wait_events) == 0


@pytest.mark.asyncio
@pytest.mark.parametrize('world', ['time-based'], indirect=True)
@pytest.mark.parametrize("progress,number_waiting", [(0, 1), (1, 0)])
async def test_wait_for_dependencies_shifted(world, progress, number_waiting):
    """
    Shifted dependency has not/has stepped far enough. Waiting is/is not
    required.
    """
    world.sims[5].progress = progress
    # Move this simulators first step to 1
    sim_under_test = world.sims[4]
    sim_under_test.next_steps = [1]
    stalled = await does_coroutine_stall(
        scheduler.wait_for_dependencies(world, sim_under_test, False)
    )
    assert stalled == bool(number_waiting)
    assert len(sim_under_test.wait_events) == number_waiting
    assert any_unset(sim_under_test.wait_events) == bool(number_waiting)


@pytest.mark.asyncio
@pytest.mark.parametrize('world', ['time-based'], indirect=True)
@pytest.mark.parametrize("lazy_stepping", [True, False])
async def test_wait_for_dependencies_lazy(world, lazy_stepping):
    """
    Test waiting for dependencies and triggering them.
    """
    sim_under_test = world.sims[1]
    sim_under_test.next_steps = [1]
    stalled = await does_coroutine_stall(
        scheduler.wait_for_dependencies(world, sim_under_test, lazy_stepping)
    )
    assert stalled == lazy_stepping
    assert len(sim_under_test.wait_events) == (1 if lazy_stepping else 0)
    assert any_unset(sim_under_test.wait_events) == lazy_stepping
    if lazy_stepping:
        assert not world.sims[1].successors[world.sims[2]].wait_lazy.is_set()
        await does_coroutine_stall(scheduler.wait_for_dependencies(world, sim_under_test, True))
        assert len(sim_under_test.wait_events) == 1
        assert any_unset(sim_under_test.wait_events) == True


@pytest.mark.parametrize('world', ['time-based'], indirect=True)
def test_get_input_data(world):
    """
    Simple test for get_input_data().
    """
    heappush(world.sims[2].next_steps, 0)
    world.sims[0].outputs = {0: {'1': {'x': 0, 'y': 1}}}
    world.sims[1].outputs = {0: {'2': {'x': 2, 'z': 4}}}
    world.sims[2].set_data_inputs = {'0': {'in': {'3': 5}, 'spam': {'3': 'eggs'}}}
    world.df_graph[0][2]['cached_connections'] = [('1', '0', [('x', 'in')])]
    world.df_graph[1][2]['cached_connections'] = [('2', '0', [('z', 'in')])]
    world.cache_dependencies()
    data = scheduler.get_input_data(world, world.sims[2])
    assert data == {'0': {
        'in': {'0.1': 0, '1.2': 4, '3': 5},
        'spam': {'3': 'eggs'},
    }}


@pytest.mark.parametrize('world', ['time-based'], indirect=True)
def test_get_input_data_shifted(world):
    """
    Getting input data transmitted via a shifted connection.
    """
    heappush(world.sims[4].next_steps, 0)
    world.sims[5].outputs = {-1: {'1': {'z': 7}}}
    world.df_graph[5][4]['cached_connections'] = [('1', '0', [('z', 'in')])]
    world.cache_dependencies()
    data = scheduler.get_input_data(world, world.sims[4])
    assert data == {'0': {'in': {'5.1': 7}}}


@pytest.mark.parametrize('world,next_steps,next_step_s1,expected',
                         [('time-based', [], 2, 5), ('time-based', [4], 2, 3),
                             ('event-based', [3], None, 2),
                             ('event-based', [3], 2, 1)], indirect=['world'])
def test_get_max_advance(world, next_steps, next_step_s1, expected):
    sim = world.sims[2]
    sim.next_steps = next_steps
    sim.tqdm = tqdm(disable=True)
    heappush(sim.next_steps, 1)

    # In the event-based world, sims 0 and 1 are triggering ancestors of sim 2:
    world.sims[0].next_steps = [3]
    if next_step_s1 is not None:
        heappush(world.sims[1].next_steps, next_step_s1)

    max_advance = scheduler.get_max_advance(world, sim, until=5)
    assert max_advance == expected


# TODO: Implement test/parameter for new API (passing max_advance)
@pytest.mark.asyncio
@pytest.mark.parametrize('world', ['time-based', 'event-based'], indirect=True)
async def test_step(world):
    inputs = {}
    sim = world.sims[0]
    sim.tqdm = tqdm(disable=True)
    heappush(sim.next_steps, 0)
    assert (sim.last_step, sim.next_steps[0]) == (-1, 0)

    progress = await scheduler.step(world, sim, inputs, 0)
    assert (sim.last_step, progress) == (0, 1)


# TODO: Test also for output_time if 'time' is indicated by event-based sims
@pytest.mark.asyncio
@pytest.mark.parametrize('world, cache',
                         [('time-based', True),
                          ('event-based', False)], indirect=['world'])
async def test_get_outputs(world, cache):
    world.use_cache = cache
    world.df_graph[0][2]['dataflows'] = [('1', '0', [('x', 'in')])]
    sim = world.sims[0]
    sim.outputs = {} if cache else None
    sim.output_request = {0: ['x', 'y']}
    sim.last_step = 0 
    sim.output_time = -1
    sim.tqdm = tqdm(disable=True)

    await scheduler.get_outputs(world, sim, progress=2)

    expected_output_cache = {
        0: {
            '0': {'x': 0, 'y': 1},
        },
        1: {
            '0': {'x': 0, 'y': 1},
        }
    }

    if cache:
        assert sim.get_output_for(0) == expected_output_cache[0]
        assert sim.get_output_for(1) == expected_output_cache[1]
    else:
        with pytest.raises(AttributeError):
            sim.get_output_for(0)
        with pytest.raises(AttributeError):
            sim.get_output_for(1)

    assert sim.output_time == 0


@pytest.mark.asyncio
@pytest.mark.parametrize('world', ['event-based'], indirect=True)
async def test_get_outputs_buffered(world: scenario.World):
    sim = world.sims[0]
    sim.outputs = {}
    sim.last_step = 0
    sim.tqdm = tqdm(disable=True)
    sim.output_request = {0: ['x', 'y', 'z']}
    sim.output_to_push = {
        ('0', 'x'): [(world.sims[2], 0, '0', 'in')],
        ('0', 'z'): [(world.sims[1], 0, '0', 'in')],
    }

    await scheduler.get_outputs(world, sim, progress=0)
    assert world.sims[2].timed_input_buffer.input_queue == [(0, 0, '0.0', '0', 'in', 0)]
    assert world.sims[1].timed_input_buffer.input_queue == []


@pytest.mark.parametrize("world", ["event-based"], indirect=True)
@pytest.mark.parametrize(
    "too_many_iterations",
    [True, False],
)
def test_treat_cycling_output(
    world: scenario.World, 
    too_many_iterations: bool,
    capsys,
):
    """
    Tests if progress is adjusted when a triggering cycle could cause
    an earlier step than predicted by get_max_advance function, or if an error
    is risen if the maximum iteration count is reached.
    """
    sim = world.sims[4]

    sim.self_trigger_times[("1", "x")] = 0
    if too_many_iterations:
        sim.same_time_steps = world.max_loop_iterations

    sim.last_step = sim.progress = output_time = 1
    data = {"1": {"x": 1}}
    if too_many_iterations:
        with pytest.raises(exceptions.SimulationError):
            scheduler.treat_cycling_output(world, sim, data, output_time, progress=2)
    else:
        assert (
            scheduler.treat_cycling_output(world, sim, data, output_time, progress=2)
            == 1
        )


@pytest.mark.parametrize('world', ['event-based'], indirect=True)
@pytest.mark.parametrize('output_time, next_steps', [(1, [1, 2]), (2, [2]), (3, [2, 3])])
@pytest.mark.parametrize('progress, pop_wait', [(2, False), (3, True)])
def test_notify_dependencies(world, output_time, next_steps, progress, pop_wait):
    sim = world.sims[0]
    sim.progress = 0

    world.df_graph[0][2]['dataflows'] = [('1', '0', [('x', 'in')])]
    world.cache_dependencies()
    world.sims[0].successors[world.sims[2]].wait_data.clear()
    sim.data = {'1': {'x': 1}}
    sim.output_time = output_time

    heappush(world.sims[2].next_steps, 2)
    world.sims[2].has_next_step.set()

    scheduler.notify_dependencies(world, sim, progress)

    assert sim.progress == progress
    assert world.sims[2].next_steps == next_steps


@pytest.mark.parametrize('world', ['event-based'], indirect=True)
def test_notify_dependencies_trigger(world):
    sim = world.sims[0]
    sim.progress = 0

    world.df_graph[0][2]['dataflows'] = [('1', '0', [('x', 'in')])]
    world.cache_dependencies()
    sim.data = {'1': {'x': 1}}
    sim.output_time = 1

    world.sims[2].has_next_step.clear()

    scheduler.notify_dependencies(world, sim, progress=1)

    assert world.sims[2].next_steps == [1]
    assert world.sims[2].has_next_step.is_set()


@pytest.mark.parametrize('world', ['time-based'], indirect=True)
def test_prune_dataflow_cache(world):
    world._df_cache = True
    world.sims[0].outputs = {
        0: {'spam': 'eggs'},
        1: {'foo': 'bar'},
    }
    for s in world.sims.values():
        s.last_step = 1
        s.tqdm = tqdm(disable=True)
    scheduler.prune_dataflow_cache(world)

    assert world.sims[0].outputs == {
        1: {'foo': 'bar'},
    }


@pytest.mark.asyncio
@pytest.mark.parametrize('world', ['time-based'], indirect=True)
async def test_get_outputs_shifted(world):
    sim = world.sims[5]
    sim.outputs = {}
    sim.output_request = {0: ['x', 'y']}
    world.cache_dependencies()
    checked_event = world.sims[5].successors[world.sims[4]].wait_data
    checked_event.clear()
    sim.type = 'time-based'
    sim.progress = 1
    sim.last_step = 1
    sim.tqdm = tqdm(disable=True)
    heappush(world.sims[4].next_steps, 2)

    await scheduler.get_outputs(world, sim, progress=2)
    scheduler.notify_dependencies(world, sim, progress=2)
    scheduler.prune_dataflow_cache(world)
    assert checked_event.is_set()
    assert sim.outputs[1] == {
        '0': {'x': 0, 'y': 1},
    }


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
    sims[1].progress = 4
    assert scheduler.get_progress(sims, 4) == 100
