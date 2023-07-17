"""
This module is responsible for performing the simulation of a scenario.
"""
from __future__ import annotations

from heapq import heappush, heappop
from loguru import logger
import networkx as nx
from time import perf_counter
import asyncio

from mosaik_api.types import InputData, OutputData, SimId, Time
from tqdm import tqdm
from mosaik.dense_time import DenseTime

from mosaik.exceptions import (ScenarioError, SimulationError, WakeUpException, NoStepException)
from mosaik.simmanager import FULL_ID, SimRunner

from typing import TYPE_CHECKING, Coroutine, Tuple
if TYPE_CHECKING:
    from typing import Dict, List, Optional
    from mosaik.scenario import World


SENTINEL = object()


async def run(
    world: World,
    until: int,
    rt_factor: Optional[float] = None,
    rt_strict: bool = False,
    lazy_stepping: bool = True,
):
    """
    Run the simulation for a :class:`~mosaik.scenario.World` until
    the simulation time *until* has been reached.

    Return the final simulation time.

    See :meth:`mosaik.scenario.World.run()` for a detailed description of the
    *rt_factor* and *rt_strict* arguments.
    """
    world.until = until

    if rt_factor is not None and rt_factor <= 0:
        raise ValueError('"rt_factor" is %s but must be > 0"' % rt_factor)
    if rt_factor is not None:
        # Adjust rt_factor to the time_resolution:
        rt_factor *= world.time_resolution
    world.rt_factor = rt_factor

    setup_done_events: List[asyncio.Task] = []
    for sim in world.sims.values():
        sim.tqdm.set_postfix_str('setup')
        # Send a setup_done event to all simulators
        setup_done_events.append(world.loop.create_task(sim.setup_done()))

    # Wait for all answers to be here
    await asyncio.gather(*setup_done_events)

    # Start simulator processes
    processes: List[asyncio.Task] = []
    for sim in world.sims.values():
        process = world.loop.create_task(
            sim_process(world, sim, until, rt_factor, rt_strict, lazy_stepping)
        )

        sim.task = process
        processes.append(process)

    # Wait for all processes to be done
    await asyncio.gather(*processes)


async def sim_process(
    world: World,
    sim: SimRunner,
    until: int,
    rt_factor: Optional[float],
    rt_strict: bool,
    lazy_stepping: bool,
):
    """
    Coroutine running the simulator *sim*.
    """
    sim.started = True
    sim.rt_start = rt_start = perf_counter()

    try:
        advance_progress(sim, world)
        while await next_step_settled(sim, world.until):
            warn_if_successors_terminated(world, sim)
            await rt_sleep(rt_factor, rt_start, sim, world)
            sim.tqdm.set_postfix_str('await input')
            await wait_for_dependencies(world, sim, lazy_stepping)
            sim.current_step = heappop(sim.next_steps)
            if sim.current_step != sim.progress.value:
                raise SimulationError(
                    f'Simulator {sim.sid} is trying to perform a step at time {sim.current_step}, '
                    f'but it has already progressed to time {sim.progress.value}.'
                )
            if sim.current_step.microstep >= world.max_loop_iterations:
                raise SimulationError(
                    f"Simulator {sim.sid} has performed step {sim.current_step.time} "
                    f"more than {world.max_loop_iterations} times. This might indicate "
                    "that you have run into an infinite loop. If not, you can increase "
                    "max_loop_iterations to get rid of this warning."
                )
            input_data = get_input_data(world, sim)
            max_advance = get_max_advance(world, sim, until)
            await step(world, sim, input_data, max_advance)
            rt_check(rt_factor, rt_start, rt_strict, sim)
            await get_outputs(world, sim)
            logger.trace("{sim.sid} completed step {step}", sim=sim, step=sim.current_step)
            sim.current_step = None
            notify_dependencies(world, sim)
            for isim in world.sims.values():
                advance_progress(isim, world)
            world.sim_progress = get_progress(world.sims, until)
            world.tqdm.update(get_avg_progress(world.sims, until) - world.tqdm.n)
            if world.use_cache:
                prune_dataflow_cache(world)
        sim.tqdm.set_postfix_str('done')
    except ConnectionError as e:
        raise SimulationError('Simulator "%s" closed its connection.' %
                              sim.sid, e)


async def next_step_settled(sim: SimRunner, until: Time) -> bool:
    # When deciding when the next step will happen, we have two numbers
    # that approach each other: The earliest currently scheduled next
    # step (which might still go down) and the earliest potential next
    # step based on the rest of the simulation, which we call the
    # simulator's progress and which can only go up.
    # Once these two numbers meet, we know that that time is the next
    # step.
    # As a slight complication, we also need to watch out for the end
    # of the simulation. Once that is reached, we also return, albeit
    # without having found a next step.
    sim.tqdm.set_postfix_str('await step')
    while sim.progress.value.time < until:
        if sim.next_steps and sim.next_steps[0] == sim.progress.value:
            return True
        else:
            await_time = sim.next_steps[0] if sim.next_steps else DenseTime(until)
            _, pending = await asyncio.wait(
                [
                    asyncio.create_task(sim.progress.has_reached(await_time)),
                    asyncio.create_task(sim.newer_step.wait()),
                ],
                return_when="FIRST_COMPLETED"
            )
            sim.newer_step.clear()
            for task in pending: task.cancel()
    return False


def warn_if_successors_terminated(world: World, sim: SimRunner):
    if 'warn_if_successors_terminated' in world.config:
        should_warn = world.config['warn_if_successors_terminated']
    else:
        should_warn = bool(sim.successors)

    if should_warn and all(suc_sim.task.done() for suc_sim in sim.successors):
        logger.warning(
            f"Simulator {sim.sid}'s output is not used anymore put it is still running."
        )


async def rt_sleep(
    rt_factor: Optional[float],
    rt_start: float,
    sim: SimRunner,
    world: World
) -> None:
    """
    If in real-time mode, check if to sleep and do so if necessary.
    """
    if rt_factor:
        rt_passed = perf_counter() - rt_start
        sleep = (rt_factor * sim.next_steps[0].time) - rt_passed
        if sleep > 0:
            sim.tqdm.set_postfix_str('sleeping')
            await asyncio.sleep(sleep)


async def wait_for_dependencies(
    world: World,
    sim: SimRunner,
    lazy_stepping: bool
) -> None:
    """
    Wait until all simulators that can provide input for this simulator have run for
    this step.

    Also notify any simulator that is already waiting to perform its next step.

    *world* is a mosaik :class:`~mosaik.scenario.World`.
    """
    futures: List[Coroutine] = []
    events: List[asyncio.Event] = []
    next_step = sim.next_steps[0]

    # Check if all predecessors have stepped far enough
    # to provide the required input data for us:
    for pre_sim, info in sim.predecessors.items():
        # Wait for dep_sim if it hasn't progressed until actual time step:
        if info.is_weak:
            futures.append(pre_sim.progress.has_reached(next_step))
        else:
            futures.append(pre_sim.progress.has_passed(next_step - DenseTime(info.time_shift)))

    for post_sim, info in sim.successors.items():
        if lazy_stepping or info.pred_waiting:
            futures.append(post_sim.progress.has_reached(next_step))
    # Check if a successor may request data from us.
    # We cannot step any further until the successor may no longer require
    # data for [last_step, next_step) from us:
    # if not world.rt_factor:
    #     for suc_sim, info in sim.successors.items():
    #         if info.pred_waiting and suc_sim.progress.value < next_step:
    #             evt = info.wait_async
    #             evt.clear()
    #             events.append(evt)
    #         elif lazy_stepping:
    #             if not info.wait_lazy.is_set():
    #                 events.append(info.wait_lazy)
    #             elif suc_sim.next_steps and suc_sim.progress.value < next_step:
    #                 evt = info.wait_lazy
    #                 evt.clear()
    #                 events.append(evt)
    # sim.wait_events = events

    # if events:
    #     check_and_resolve_deadlocks(sim, waiting=True)

    await asyncio.gather(*futures) #, *(evt.wait() for evt in events))


def get_input_data(world: World, sim: SimRunner) -> InputData:
    """
    Return a dictionary with the input data for *sim*.

    The dict will look like::

        {
            'eid': {
                'attrname': {'src_eid_0': val_0, ... 'src_eid_n': val_n},
                ...
            },
            ...
        }

    For every entity, there is an entry in the dict and each entry is itself
    a dict with attributes and a list of values. This is, because we may have
    inputs from multiple simulators (e.g., different consumers that provide
    loads for a node in a power grid) and cannot know how to aggregate that
    data (sum, max, ...?).

    *world* is a mosaik :class:`~mosaik.scenario.World`.
    """
    assert sim.current_step is not None
    input_data = sim.inputs_from_set_data
    sim.inputs_from_set_data = {}
    recursive_union(input_data, sim.persistent_inputs)
    input_data = sim.timed_input_buffer.get_input(input_data, sim.current_step.time)

    for src_sim, info in sim.predecessors.items():
        dataflows = info.pulled_inputs
        if not dataflows:
            continue
        t = sim.current_step.time - info.time_shift
        cache_slice = src_sim.get_output_for(t)
        for src_eid, dest_eid, attrs in dataflows:
            for src_attr, dest_attr in attrs:
                try:
                    val = cache_slice[src_eid][src_attr]
                except KeyError:
                    logger.warning(
                        f"Simulator {src_sim.sid}'s entity {src_eid} did not "
                        f"produce output on its persistent attribute {src_attr} "
                        "during its last step. However, this value is now required "
                        f"by simulator {sim.sid}. This usually results from "
                        "attributes that are marked persistent despite working "
                        "like events. This will be an error in future versions of "
                        "mosaik."
                    )
                    val = None
                input_vals = input_data.setdefault(dest_eid, {}) \
                    .setdefault(dest_attr, {})
                input_vals[FULL_ID % (src_sim.sid, src_eid)] = val

    recursive_update(sim.persistent_inputs, input_data)

    return input_data


def recursive_union(d, u):
    for k, v in u.items():
        if isinstance(v, dict):
            d[k] = recursive_union(d.get(k, {}), v)
        else:
            d[k] = v
    return d


def recursive_update(d, u):
    for k, v in d.items():
        if isinstance(v, dict):
            d[k] = recursive_update(v, u[k])
        else:
            d[k] = u[k]
    return d


def get_max_advance(world: World, sim: SimRunner, until: int) -> int:
    """
    Checks how far *sim* can safely advance its internal time during next step
    without causing a causality error.
    """
    ancs_next_steps: List[DenseTime] = []
    for anc_sim, distance in sim.triggering_ancestors:
        if anc_sim.next_steps:
            ancs_next_steps.append(anc_sim.next_steps[0] + distance)

    own_next_step = [sim.next_steps[0]] if sim.next_steps else []

    return min([*ancs_next_steps, *own_next_step, DenseTime(until)]).time


async def step(
    world: World,
    sim: SimRunner,
    inputs: InputData,
    max_advance: int
):
    """
    Advance (step) a simulator *sim* with the given *inputs*. Return an
    event that is triggered when the step was performed.

    *inputs* is a dictionary, that maps entity IDs to data dictionaries which
    map attribute names to lists of values (see :func:`get_input_data()`).

    *max_advance* is the simulation time until the simulator can safely advance
    it's internal time without causing any causality errors.
    """
    assert sim.current_step is not None
    sim.tqdm.set_postfix_str('stepping')
    sim.is_in_step = True
    next_step_time = await sim.step(sim.current_step.time, inputs, max_advance)
    sim.last_step = sim.current_step
    sim.is_in_step = False


    if next_step_time is not None:
        if type(next_step_time) != int:
            raise SimulationError(
                f'the next step time returned by the step method must be of type int, '
                f'but is of type {type(next_step_time)} for simulator "{sim.sid}"'
            )
        if next_step_time <= sim.current_step.time:
            raise SimulationError(
                f'the next step time returned by step must be later than the current '
                f"step's time, but {next_step_time} <= {sim.current_step.time} "
                f'for simulator "{sim.sid}"'
            )

        if next_step_time < world.until:
            sim.schedule_step(DenseTime(next_step_time))
            sim.next_self_step = next_step_time

    if sim.type == 'time-based':
        assert next_step_time, "A time-based simulator must always return a next step"


def rt_check(
    rt_factor: Optional[float],
    rt_start: float,
    rt_strict: bool,
    sim: SimRunner
):
    """
    Check if simulation is fast enough for a given real-time factor.
    """
    if rt_factor:
        rt_passed = perf_counter() - rt_start
        delta = rt_passed - (rt_factor * sim.last_step.time)
        if delta > 0:
            if rt_strict:
                raise RuntimeError(
                    f'Simulation too slow for real-time factor {rt_factor}'
                )
            else:
                logger.warning(
                    'Simulation too slow for real-time factor {rt_factor} - {delta}s '
                    'behind time.',
                    rt_factor=rt_factor,
                    delta=delta
                )


async def get_outputs(world: World, sim: SimRunner):
    """
    Wait for all required output data from a simulator *sim*.

    *world* is a mosaik :class:`~mosaik.scenario.World`.
    """
    assert sim.current_step is not None
    sid = sim.sid
    outattr = sim.output_request
    if outattr:
        sim.tqdm.set_postfix_str('get_data')
        data = await sim.get_data(outattr)

        output_time: int
        output_time = data.get('time', sim.last_step.time)  # type: ignore
        if output_time == sim.current_step.time:
            output_dense_time = sim.current_step
        else:
            output_dense_time = DenseTime(output_time)
        sim.output_time = output_dense_time
        if sim.last_step.time > output_time:
            raise SimulationError(
                'Output time (%s) is not >= time (%s) for simulator "%s"'
                % (output_time, sim.last_step, sim.sid))

        # Fill output cache. This will repeat some data that is also
        # pushed forward below, but it is faster to just save everything
        # than filter out this data here.
        if sim.outputs is not None:
            sim.outputs[output_time] = data

        # Push forward certain data
        for (src_eid, src_attr), destinations in sim.output_to_push.items():
            try:
                val = data[src_eid][src_attr]
                for dest_sim, time_shift, dest_eid, dest_attr in destinations:
                    dest_sim.timed_input_buffer.add(
                        output_time + time_shift, sid, src_eid, dest_eid, dest_attr, val
                    )
            except KeyError:
                pass
        sim.data = data 


def notify_dependencies(world: World, sim: SimRunner) -> None:
    """
    Notify all simulators waiting for us.
    """
    # Notify simulators waiting for inputs from us.
    for dest_sim, info in sim.successors.items():
        for eid, attr in info.trigger:
            data_eid = sim.data.get(eid, {})
            if attr in data_eid:
                dest_input_time = sim.output_time + info.delay
                if dest_input_time < world.until:
                    dest_sim.schedule_step(dest_input_time)
                break  # Further triggering attributes would only schedule the same event


def prune_dataflow_cache(world: World):
    """
    Prunes the dataflow cache.
    """
    if not world.use_cache:
        return
    min_cache_time = min(s.last_step.time for s in world.sims.values())
    for sim in world.sims.values():
        if sim.outputs:
            sim.outputs = {
                time: cache
                for time, cache in sim.outputs.items()
                if time >= min_cache_time
            }


def get_progress(sims: Dict[SimId, SimRunner], until: int) -> float:
    """
    Return the current progress of the simulation in percent.
    """
    times = [sim.progress.value.time for sim in sims.values()]
    avg_time = sum(times) / len(times)
    return avg_time * 100 / until


def get_avg_progress(sims: Dict[SimId, SimRunner], until: int) -> int:
    """Get the average progress of all simulations (in time steps)."""
    times = [min(until, sim.progress.value.time + 1) for sim in sims.values()]
    return sum(times) // len(times)


def advance_progress(sim: SimRunner, world: World):
    pre_sim_induced_progress: List[DenseTime] = [
        pre_sim.next_steps[0] + distance
        for pre_sim, distance in sim.triggering_ancestors
        if pre_sim.next_steps
    ]

    next_step_progress: List[DenseTime] = [sim.next_steps[0]] if sim.next_steps else []
    current_step_prog = [sim.current_step] if sim.current_step else []
    new_progress = min([
        *pre_sim_induced_progress,
        *next_step_progress,
        *current_step_prog,
        DenseTime(world.until),
    ])
    sim.progress.set(new_progress)
    sim.tqdm.update(new_progress.time - sim.tqdm.n)


def check_and_resolve_deadlocks(
    sim: SimRunner,
    waiting: bool = False,
    end: bool = False
) -> None:
    """
    Checks for deadlocks which can occur when all simulators are either waiting
    for a next step or for dependencies, or have finished already.
    """
    waiting_sims = [] if not waiting else [sim]
    for isim in sim.related_sims:
        if not isim.started:
            # isim hasn't done anything yet. If there are deadlocks
            # during start-up, we will notice this during the last
            # simulators first call to check_and_resolve_deadlocks.
            break
        elif isim.task.done() or not isim.has_next_step.is_set():
            # isim has finished already or has no next step
            continue
        elif not isim.wait_events or all(evt.is_set() for evt in isim.wait_events):
            # isim hasn't executed `wait_for_dependencies` yet and will
            # perform a deadlock check again if necessary or is not waiting.
            break
        else:
            waiting_sims.append(isim)
    else:
        # This part will only be reached if all simulators either have no next
        # step or are waiting for dependencies.
        if waiting_sims:
            sim_queue = []
            for isim in waiting_sims:
                heappush(sim_queue, (isim.next_steps[0], isim.rank, isim))
            clear_wait_events(sim_queue[0][2])
        else:
            if not end:
                # None of interdependent sims has a next step, isim can stop.
                raise NoStepException

    # If we have no next step, we have to check if a predecessor is waiting for
    # us for async. requests or lazily:
    if not sim.next_steps:
        for pre_sim, info in sim.predecessors.items():
            info.wait_async.set()

def clear_wait_events(sim: SimRunner) -> None:
    """
    Clear/succeed all wait events *sim* is waiting for.
    """
    for info in sim.successors.values():
        info.wait_async.set()


def clear_wait_events_dependencies(sim: SimRunner) -> None:
    """
    Clear/succeed all wait events over which other simulators are waiting for
    *sim*.
    """
    for info in sim.predecessors.values():
        info.wait_async.set()
