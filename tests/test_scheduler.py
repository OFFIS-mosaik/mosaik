from __future__ import annotations

import asyncio
from heapq import heappop, heappush
from mosaik_api_v3 import InputData
import pytest
from pytest import mark, param
from tqdm import tqdm
from typing import Any, Coroutine, Iterable, List

from mosaik import exceptions, scenario, scheduler, simmanager, World
from mosaik.adapters import init_and_get_adapter
from mosaik.progress import Progress
from mosaik.proxies import LocalProxy
from mosaik.simmanager import SimRunner
from mosaik.tiered_time import TieredInterval, TieredTime

from tests.mocks.simulator_mock import SimulatorMock


async def does_coroutine_stall(coro: Coroutine[Any, Any, Any], max_pass_backs: int = 0):
    """Executes the given coroutine as a task and give control back
    to it `pass_backs` times. If it doesn't complete in that time,
    the task is cancelled.
    
    Returns ``False`` if the coroutine did not complete in the given
    attempts, ``True`` otherwise.
    """
    task = asyncio.create_task(coro)
    async def canceller():
        for _ in range(max_pass_backs):
            await asyncio.sleep(0)
        if not task.done():
            task.cancel()
    await asyncio.gather(task, canceller(), return_exceptions=True)
    return task.cancelled()


@pytest.fixture(name='world')
def world_fixture(request: pytest.FixtureRequest):
    """This fixture provides an example scenario for testing the
    scheduler. It looks like this:

    ┌───────┐                               ┌──────────────────────┐
    │ Sim-0 ├─────────┐                     │ ┌───────┐            │
    └───────┘         ▼                     │ │ Sim-4 │            │
                  ┌───────┐     ┌───────┐   │ └─┬─────┘            │
                  │ Sim-2 ├────►│ Sim-3 │   │   ▼   ▲time-shifted/ │
                  └───────┘     └───────┘   │ ┌─────┴─┐   weak     │
    ┌───────┐         ▲                     │ │ Sim-5 │            │
    │ Sim-1 ├─────────┘                     │ └───────┘            │
    └───────┘                               └──────────────────────┘
    
    All connections are non-triggering if the param value is
    "time-based", and are triggering if the param value is
    "event-based". The edge marked time-shifted/weak is time-shifted or
    weak in these two cases, respectively. The box (indicating a
    simulator group) only exists in the event-based case.
    """
    event_based = (request.param == 'event-based')
    world = scenario.World({})
    sims: List[SimRunner] = []
    for i in range(6):
        sim_id = f"Sim-{i}"
        proxy = LocalProxy(SimulatorMock(request.param), simmanager.MosaikRemote(world, sim_id))
        proxy = world.loop.run_until_complete(
            init_and_get_adapter(proxy, sim_id, {"time_resolution": 1.0})
        )
        sim = SimRunner(sim_id, proxy)
        world.sims[sim_id] = sim
        sims.append(sim)
    class DummyTask:
        def done(self):
            return False
    for sim in world.sims.values():
        sim.task = DummyTask()
    
    for src, dest in [(0, 2), (1, 2), (2, 3)]:
        sims[src].successors[sims[dest]] = TieredInterval(0)
        sims[dest].input_delays[sims[src]] = TieredInterval(0)
        if event_based:
            sims[src].triggers.setdefault(('1', 'x'), []).append((sims[dest], TieredInterval(0)))
    if event_based:
        sims[4].successors[sims[5]] = TieredInterval(0, 0)
        sims[5].input_delays[sims[4]] = TieredInterval(0, 0)
        sims[5].successors[sims[4]] = TieredInterval(0, 0)
        sims[4].input_delays[sims[5]] = TieredInterval(0, 1)
        sims[4].triggers[('1', 'x')] = [(sims[5], TieredInterval(0, 0))]
        sims[5].triggers[('1', 'x')] = [(sims[4], TieredInterval(0, 1))]
    else:
        sims[4].successors[sims[5]] = TieredInterval(0)
        sims[5].input_delays[sims[4]] = TieredInterval(0)
        sims[5].successors[sims[4]] = TieredInterval(0)
        sims[4].input_delays[sims[5]] = TieredInterval(1)


    world.until = 4
    world.rt_factor = None
    world.cache_triggering_ancestors()
    yield world
    world.shutdown()


def test_run(monkeypatch):
    """Test if a process is started for every simulation."""
    world = scenario.World({})

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
        
    world.sims = {i: SimRunner(i, proxy) for i in range(2)}

    monkeypatch.setattr(scheduler, 'sim_process', dummy_proc)
    try:
        world.run(until=1)
        for sim in world.sims.values():
            assert sim.proc_started
    finally:
        world.shutdown()


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

    def advance_progress(sim, world):
        raise ConnectionError(1337, 'noob')

    monkeypatch.setattr(scheduler, 'advance_progress', advance_progress)

    with pytest.raises(exceptions.SimulationError) as excinfo:
        await scheduler.sim_process(None, Sim(), None, 1, False, False)
    assert str(excinfo.value) == ('[Errno 1337] noob: Simulator "spam" closed '
                                  'its connection.')


def any_unset(events: Iterable[asyncio.Event]) -> bool:
    """
    Returns whether any of the events of the given iterable is unset.
    """
    return any(not e.is_set() for e in events)


@pytest.mark.asyncio
@pytest.mark.parametrize('world', ['time-based', 'event-based'], indirect=True)
@pytest.mark.parametrize("weak, number_waiting", [
    param(True, 2, marks=mark.weak),
    (False, 2),
])
async def test_wait_for_dependencies(world: World, weak: bool, number_waiting: int):
    """
    Test waiting for dependencies and triggering them.
    """
    test_sim: SimRunner = world.sims["Sim-2"]
    pred_sim: SimRunner = world.sims["Sim-1"]
    heappush(test_sim.next_steps, TieredTime(0))
    test_sim.input_delays[pred_sim] = TieredInterval(0, 1)
    stalled = await does_coroutine_stall(
        scheduler.wait_for_dependencies(test_sim, True)
    )
    assert stalled


@pytest.mark.asyncio
@pytest.mark.parametrize('world', ['time-based'], indirect=True)
async def test_wait_for_dependencies_all_done(world: World):
    """
    All dependencies already stepped far enough. No waiting required.
    """
    heappush(world.sims["Sim-2"].next_steps, TieredTime(0))
    for dep_sid in ["Sim-0", "Sim-1"]:
        world.sims[dep_sid].progress.time = TieredTime(1)
    stalled = await does_coroutine_stall(
        scheduler.wait_for_dependencies(world.sims["Sim-2"], True),
        max_pass_backs=3,
    )
    assert not stalled


@pytest.mark.asyncio
@pytest.mark.parametrize('world', ['time-based'], indirect=True)
@pytest.mark.parametrize("progress, should_stall", [(0, True), (1, False)])
async def test_wait_for_dependencies_shifted(world: World, progress: int, should_stall: bool):
    """
    Shifted dependency has not/has stepped far enough. Waiting is/is not
    required.
    """
    world.sims["Sim-5"].progress = Progress(TieredTime(progress))
    # Move this simulators first step to 1
    sim_under_test = world.sims["Sim-4"]
    sim_under_test.next_steps = [TieredTime(1)]
    stalled = await does_coroutine_stall(
        scheduler.wait_for_dependencies(sim_under_test, lazy_stepping=False),
        max_pass_backs=3,
    )
    assert stalled == should_stall


@pytest.mark.asyncio
@pytest.mark.parametrize('world', ['time-based'], indirect=True)
@pytest.mark.parametrize("lazy_stepping", [True, False])
async def test_wait_for_dependencies_lazy(world: World, lazy_stepping: bool):
    """
    Test waiting for dependencies and triggering them.
    """
    sim_under_test = world.sims["Sim-1"]
    sim_under_test.next_steps = [TieredTime(1)]
    stalled = await does_coroutine_stall(
        scheduler.wait_for_dependencies(sim_under_test, lazy_stepping)
    )
    assert stalled == lazy_stepping
    if lazy_stepping:
        await does_coroutine_stall(
            scheduler.wait_for_dependencies(sim_under_test, True)
        )


@pytest.mark.parametrize('world', ['time-based'], indirect=True)
def test_get_input_data(world: World):
    """
    Simple test for get_input_data().
    """
    sim_0 = world.sims["Sim-0"]
    sim_1 = world.sims["Sim-1"]
    sim_2 = world.sims["Sim-2"]
    sim_2.current_step = TieredTime(0)
    sim_0.outputs = {0: {'1': {'x': 0, 'y': 1}}}
    sim_1.outputs = {0: {'2': {'x': 2, 'z': 4}}}
    sim_2.inputs_from_set_data = {
        '0': {'in': {'3': 5}, 'spam': {'3': 'eggs'}}
    }
    sim_2.pulled_inputs[(sim_0, TieredInterval(0))] = set([(('1', 'x'), ('0', 'in'))])
    sim_2.pulled_inputs[(sim_1, TieredInterval(0))] = set([(('2', 'z'), ('0', 'in'))])
    data = scheduler.get_input_data(world, sim_2)
    assert data == {'0': {
        'in': {'Sim-0.1': 0, 'Sim-1.2': 4, '3': 5},
        'spam': {'3': 'eggs'},
    }}


@pytest.mark.parametrize('world', ['time-based'], indirect=True)
def test_get_input_data_shifted(world: World):
    """
    Getting input data transmitted via a shifted connection.
    """
    sim_4 = world.sims["Sim-4"]
    sim_5 = world.sims["Sim-5"]
    sim_4.current_step = TieredTime(0)
    sim_5.outputs = {-1: {'1': {'z': 7}}}
    sim_4.pulled_inputs[(sim_5, TieredInterval(1))] = set([(('1', 'z'), ('0', 'in'))])
    data = scheduler.get_input_data(world, world.sims["Sim-4"])
    assert data == {'0': {'in': {'Sim-5.1': 7}}}


@pytest.mark.parametrize(
    'world, next_steps, next_step_s1, expected',
    [
        ('time-based', [], TieredTime(2), 5),
        ('time-based', [TieredTime(4)], TieredTime(2), 3),
        ('event-based', [TieredTime(3)], None, 2),
        ('event-based', [TieredTime(3)], TieredTime(2), 1),
    ],
    indirect=['world'],
)
def test_get_max_advance(
    world: World,
    next_steps: List[TieredTime],
    next_step_s1: TieredTime | None,
    expected: int,
):
    sim = world.sims["Sim-2"]
    sim.next_steps = next_steps
    sim.tqdm = tqdm(disable=True)
    heappush(sim.next_steps, TieredTime(1))
    sim.current_step = heappop(sim.next_steps)

    # In the event-based world, Sim-0 and Sim-1 are triggering ancestors
    # of Sim-2:
    world.sims["Sim-0"].next_steps = [TieredTime(3)]
    if next_step_s1 is not None:
        heappush(world.sims["Sim-1"].next_steps, next_step_s1)

    max_advance = scheduler.get_max_advance(world, sim, until=5)
    assert max_advance == expected


# TODO: Implement test/parameter for new API (passing max_advance)
@pytest.mark.asyncio
@pytest.mark.parametrize('world', ['time-based', 'event-based'], indirect=True)
async def test_step(world: World):
    inputs: InputData = {}
    sim = world.sims["Sim-0"]
    sim.tqdm = tqdm(disable=True)
    if sim.type == 'event-based':
        heappush(sim.next_steps, TieredTime(0))
    assert (sim.last_step, sim.next_steps[0]) == (TieredTime(-1), TieredTime(0))
    sim.current_step = heappop(sim.next_steps)

    await scheduler.step(world, sim, inputs, 0)
    assert (sim.last_step, sim.next_steps) == (
        TieredTime(0), [TieredTime(1)] if sim.type == 'time-based' else []
    )


# TODO: Test also for output_time if 'time' is indicated by event-based sims
@pytest.mark.asyncio
@pytest.mark.parametrize('world, cache',
                         [('time-based', True),
                          ('event-based', False)], indirect=['world'])
async def test_get_outputs(world: World, cache: bool):
    world.use_cache = cache
    sim = world.sims["Sim-0"]
    sim.outputs = {} if cache else None
    sim.output_request = {0: ['x', 'y']}
    sim.last_step = TieredTime(0) 
    sim.output_time = TieredTime(-1)
    sim.tqdm = tqdm(disable=True)

    if sim.type == 'time-based':
        sim.current_step = heappop(sim.next_steps)
    else:
        sim.current_step = TieredTime(0)
    await scheduler.get_outputs(world, sim)

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
        with pytest.raises(AssertionError):
            sim.get_output_for(0)
        with pytest.raises(AssertionError):
            sim.get_output_for(1)

    assert sim.output_time == TieredTime(0)


@pytest.mark.asyncio
@pytest.mark.parametrize('world', ['event-based'], indirect=True)
async def test_get_outputs_buffered(world: scenario.World):
    sim = world.sims["Sim-0"]
    sim.outputs = {}
    sim.last_step = TieredTime(0)
    sim.current_step = TieredTime(0)
    sim.tqdm = tqdm(disable=True)
    sim.output_request = {0: ['x', 'y', 'z']}
    sim.output_to_push = {
        ('0', 'x'): [(world.sims["Sim-2"], TieredInterval(0), ('0', 'in'))],
        ('0', 'z'): [(world.sims["Sim-1"], TieredInterval(0), ('0', 'in'))],
    }

    await scheduler.get_outputs(world, sim)
    assert world.sims["Sim-2"].timed_input_buffer.input_queue == [(0, 0, 'Sim-0.0', '0', 'in', 0)]
    assert world.sims["Sim-1"].timed_input_buffer.input_queue == []


@pytest.mark.parametrize('world', ['event-based'], indirect=True)
@pytest.mark.parametrize('output_time, next_steps', [
    (TieredTime(1), [TieredTime(1), TieredTime(2)]),
    (TieredTime(2), [TieredTime(2)]),
    (TieredTime(3), [TieredTime(2), TieredTime(3)])],
)
@pytest.mark.parametrize('progress', [2, 3])
def test_notify_dependencies(
    world: World,
    output_time: TieredTime,
    next_steps: List[TieredTime],
    progress: int,
):
    sim = world.sims["Sim-0"]
    sim.progress = 0

    sim.data = {'1': {'x': 1}}
    sim.output_time = output_time

    heappush(world.sims["Sim-2"].next_steps, TieredTime(2))

    scheduler.notify_dependencies(sim)

    assert world.sims["Sim-2"].next_steps == next_steps


@pytest.mark.parametrize('world', ['event-based'], indirect=True)
def test_notify_dependencies_trigger(world: World):
    sim = world.sims["Sim-0"]
    sim.progress = Progress(TieredTime(0))

    sim.data = {'1': {'x': 1}}
    sim.output_time = TieredTime(1)
    scheduler.notify_dependencies(sim)

    assert world.sims["Sim-2"].next_steps == [TieredTime(1)]


@pytest.mark.parametrize('world', ['time-based'], indirect=True)
def test_prune_dataflow_cache(world: World):
    world.use_cache = True
    world.sims["Sim-0"].outputs = {
        0: {'spam': 'eggs'},
        1: {'foo': 'bar'},
    }
    for s in world.sims.values():
        s.last_step = TieredTime(1)
        s.tqdm = tqdm(disable=True)
    scheduler.prune_dataflow_cache(world)

    assert world.sims["Sim-0"].outputs == {
        1: {'foo': 'bar'},
    }


@pytest.mark.asyncio
@pytest.mark.parametrize('world', ['time-based'], indirect=True)
async def test_get_outputs_shifted(world: World):
    sim = world.sims["Sim-5"]
    sim.outputs = {}
    sim.output_request = {0: ['x', 'y']}
    sim.type = 'time-based'
    sim.progress = Progress(TieredTime(1))
    sim.last_step = TieredTime(1)
    sim.tqdm = tqdm(disable=True)
    heappush(world.sims["Sim-4"].next_steps, TieredTime(2))
    
    sim.current_step = heappop(sim.next_steps)
    await scheduler.get_outputs(world, sim)
    scheduler.notify_dependencies(sim)
    scheduler.prune_dataflow_cache(world)
    assert sim.outputs[1] == {
        '0': {'x': 0, 'y': 1},
    }


def test_get_progress():
    class Sim:
        def __init__(self, time):
            self.progress = Progress(TieredTime(time))

    sims = {i: Sim(0) for i in range(2)}
    assert scheduler.get_progress(sims, 4) == 0

    sims[0].progress.time = TieredTime(1)
    assert scheduler.get_progress(sims, 4) == 12.5

    sims[0].progress.time = TieredTime(2)
    assert scheduler.get_progress(sims, 4) == 25

    sims[1].progress.time = TieredTime(3)
    sims[0].progress.time = TieredTime(3)
    assert scheduler.get_progress(sims, 4) == 75

    sims[0].progress.time = TieredTime(4)
    sims[1].progress.time = TieredTime(4)
    assert scheduler.get_progress(sims, 4) == 100
