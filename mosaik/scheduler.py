"""
This module is responsible for performing the simulation of a scenario.
"""
from __future__ import annotations

from heapq import heappush, heappop
from loguru import logger
import networkx as nx
from time import perf_counter
import asyncio

from mosaik.exceptions import (SimulationError, WakeUpException, NoStepException)
from mosaik.simmanager import FULL_ID, SimRunner

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from typing import Dict, List, Optional
    from mosaik.scenario import World, InputData, OutputData, SimId


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
        # setup_done() was added in API version 2.2:
        sim.tqdm.set_postfix_str('setup')
        # Send a setup_done event to all simulators
        setup_done_events.append(asyncio.create_task(sim.proxy.setup_done()))

    # Wait for all answers to be here
    await asyncio.gather(*setup_done_events)

    # Start simulator processes
    processes: List[asyncio.Task] = []
    for sim in world.sims.values():
        process = asyncio.create_task(
            sim_process(world, sim, until, rt_factor, rt_strict, lazy_stepping)
        )

        sim.sim_proc = process
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
        keep_running = get_keep_running_func(world, sim, until, rt_factor,
                                             rt_start)
        while keep_running():
            warn_if_successors_terminated(world, sim)
            try:
                await wait_for_next_step(world, sim)
            except WakeUpException:
                # We've been woken up by a terminating predecessor.
                # Check if we can also stop or need to keep running.
                continue
            except NoStepException:
                # None of the simulators has a next step, therefore stop.
                break
            sim.interruptable = True
            while True:
                try:
                    await rt_sleep(rt_factor, rt_start, sim, world)
                    sim.tqdm.set_postfix_str('waiting')
                    await wait_for_dependencies(world, sim, lazy_stepping)
                    break
                except asyncio.CancelledError:
                    # We use cancellation as an interrupt.
                    # TODO: Find a better way to do this.
                    clear_wait_events(sim)
                    continue
            sim.interruptable = False
            if sim.next_steps[0] >= world.until:
                break
            input_data = get_input_data(world, sim)
            max_advance = get_max_advance(world, sim, until)
            progress = await step(world, sim, input_data, max_advance)
            rt_check(rt_factor, rt_start, rt_strict, sim)
            progress = await get_outputs(world, sim, progress)
            notify_dependencies(world, sim, progress)
            if world._df_cache:
                prune_dataflow_cache(world)
            world.sim_progress = get_progress(world.sims, until)
            world.tqdm.update(get_avg_progress(world.sims, until) - world.tqdm.n)
            sim.tqdm.update(sim.progress + 1 - sim.tqdm.n)
        sim.progress = until
        clear_wait_events_dependencies(sim)
        check_and_resolve_deadlocks(sim, end=True)
        # Before we stop, we wake up all dependencies who may be waiting for
        # us. They can then decide whether to also stop of if there's another
        # process left which might provide data.
        for suc_sid in world.trigger_graph.successors(sim.sid):
            if not world.sims[suc_sid].sim_proc.done():
                world.sims[suc_sid].has_next_step.set()

    except ConnectionError as e:
        raise SimulationError('Simulator "%s" closed its connection.' %
                              sim.sid, e)


def get_keep_running_func(
    world: World,
    sim: SimRunner,
    until: int,
    rt_factor: Optional[float],
    rt_start: float
):
    """
    Return a function that the :func:`sim_process()` uses to determine
    when to stop.

    Depending on whether the process has any successors in the dataflow graph,
    the condition for when to stop differs.
    """
    check_functions = []
    no_set_events = not (
        rt_factor
        and (
            sim.proxy.meta.get('set_events', False)
            or any([
                world.sims[anc_sid].proxy.meta.get('set_events', False)
                for anc_sid in nx.ancestors(world.trigger_graph, sim.sid)
            ])
        )
    )
    if no_set_events:
        if world.trigger_graph.in_degree(sim.sid) == 0:
            def check_time():
                return sim.progress < until
        else:
            def check_time():
                return sim.progress <= until

        check_functions.append(check_time)

    if sim.type != 'time-based':
        # If we are not self-stepped we can stop if all predecessors have
        # stopped and there's no step left.
        # Unless we are running in real-time mode, then we have to wait until
        # the total wall-clock time has passed.
        if not rt_factor:
            pre_processes = [
                world.sims[pre_sid].sim_proc
                for pre_sid in world.trigger_graph.predecessors(sim.sid)
            ]

            def check_trigger():
                return sim.next_steps or not all(p.done() for p in pre_processes)
        else:
            pre_sims = [
                world.sims[pre_sid]
                for pre_sid in nx.ancestors(world.trigger_graph, sim.sid)
            ]

            def check_trigger():
                return (sim.next_steps
                        or any(pre_sim.next_steps for pre_sim in pre_sims)
                        or (perf_counter() - rt_start < rt_factor * until))

        check_functions.append(check_trigger)

    def keep_running():
        return all([f() for f in check_functions])

    return keep_running


def warn_if_successors_terminated(world: World, sim: SimRunner):
    if 'warn_if_successors_terminated' in world.config:
        should_warn = world.config['warn_if_successors_terminated']
    else:
        should_warn = world.df_graph.out_degree(sim.sid) > 0

    processes = [
        world.sims[suc_sid].sim_proc
        for suc_sid in sim.successors
    ]

    if should_warn and all(process.done() for process in processes):
        logger.warning(f"Simulator {sim.sid}'s output is not used anymore put it "
                       f"is still running.")


async def wait_for_next_step(world: World, sim: SimRunner) -> None:
    """
    This coroutine checks and potentially waits for this simulator's next step.

    If a predecessor terminates, we will be awoken as well, and throw a WakeUpException.
    """
    sim.has_next_step.clear()

    if sim.next_steps:
        sim.has_next_step.set()
        sim.tqdm.set_postfix_str('no step')
        await sim.has_next_step.wait()
    else:
        try:
            if world.rt_factor:
                rt_passed = perf_counter() - sim.rt_start
                timeout = max(
                    (world.rt_factor * world.until) - rt_passed,
                    0.1 * world.rt_factor
                )
                sim.tqdm.set_postfix_str('no step')
                try:
                    await asyncio.wait_for(
                        asyncio.shield(sim.has_next_step.wait()), timeout
                    )
                except asyncio.TimeoutError:
                    raise NoStepException
            else:
                check_and_resolve_deadlocks(sim)
                sim.tqdm.set_postfix_str('no step')
                await sim.has_next_step.wait()

            # If has_next_step is triggered but there is still no new step, this
            # means that a predecessor has terminated. We return control to
            # sim_process so that it can check whether we can terminate as well.
            if not sim.next_steps:
                raise WakeUpException
        except NoStepException:
            raise NoStepException


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
        sleep = (rt_factor * sim.next_steps[0]) - rt_passed
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
    events: List[asyncio.Event] = []
    next_step = sim.next_steps[0]

    # Check if all predecessors have stepped far enough
    # to provide the required input data for us:
    for pre_sim, edge in sim.predecessors.values():
        # Wait for dep_sim if it hasn't progressed until actual time step:
        if pre_sim.progress + edge['time_shifted'] <= next_step:
            evt = edge['wait_event']
            evt.clear()
            events.append(evt)
            # To avoid deadlocks:
            if not edge['wait_lazy'].is_set():
                edge['wait_lazy'].set()

    # Check if a successor may request data from us.
    # We cannot step any further until the successor may no longer require
    # data for [last_step, next_step) from us:
    if not world.rt_factor:
        for suc_sim, edge in sim.successors.values():
            if edge['pred_waiting'] and suc_sim.progress < next_step:
                evt = edge['wait_async']
                evt.clear()
                events.append(evt)
            elif lazy_stepping:
                if not edge['wait_lazy'].is_set():
                    events.append(edge['wait_lazy'])
                elif suc_sim.next_steps and suc_sim.progress < next_step:
                    evt = edge['wait_lazy']
                    evt.clear()
                    events.append(evt)
    sim.wait_events = events

    if events:
        check_and_resolve_deadlocks(sim, waiting=True)

    await asyncio.gather(*(evt.wait() for evt in events))


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
    input_memory = sim.input_memory
    input_data = sim.input_buffer
    sim.input_buffer = {}
    recursive_union(input_data, input_memory)
    input_data = sim.timed_input_buffer.get_input(input_data, sim.next_steps[0])

    if world._df_cache is not None:
        for src_sid, (_, edge) in sim.predecessors.items():
            t = sim.next_steps[0] - edge['time_shifted']
            cache_slice = world._df_cache[t]
            dataflows = edge['cached_connections']
            for src_eid, dest_eid, attrs in dataflows:
                for src_attr, dest_attr in attrs:
                    v = cache_slice.get(src_sid, {}).get(src_eid, {})\
                        .get(src_attr, SENTINEL)
                    if v is not SENTINEL:
                        vals = input_data.setdefault(dest_eid, {}) \
                            .setdefault(dest_attr, {})
                        vals[FULL_ID % (src_sid, src_eid)] = v

    recursive_update(input_memory, input_data)

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
    ancs_next_steps = []
    for anc_sid, immediate in sim.triggering_ancestors:
        anc_sim = world.sims[anc_sid]
        if anc_sim.next_steps:
            ancs_next_steps.append(anc_sim.next_steps[0] - immediate)

    if ancs_next_steps:
        max_advance = min(ancs_next_steps)
    else:
        max_advance = until

    if len(sim.next_steps) >= 2:
        tmp = heappop(sim.next_steps)
        max_advance = min(sim.next_steps[0] - 1, max_advance)
        heappush(sim.next_steps, tmp)

    return max_advance


async def step(
    world: World,
    sim: SimRunner,
    inputs: InputData,
    max_advance: int
) -> int:
    """
    Advance (step) a simulator *sim* with the given *inputs*. Return an
    event that is triggered when the step was performed.

    *inputs* is a dictionary, that maps entity IDs to data dictionaries which
    map attribute names to lists of values (see :func:`get_input_data()`).

    *max_advance* is the simulation time until the simulator can safely advance
    it's internal time without causing any causality errors.
    """
    current_step = heappop(sim.next_steps)
    if current_step < sim.progress - 1:
        raise SimulationError(
            f'Simulator {sim.sid} is trying to perform a step at time {current_step}, '
            f'but it has already progressed to time {sim.progress}.'
        )
    sim.last_step = current_step

    sim.tqdm.set_postfix_str('stepping')
    sim.is_in_step = True
    next_step = await sim.proxy.step(current_step, inputs, max_advance)
    sim.is_in_step = False

    if next_step is not None:
        if type(next_step) != int:
            raise SimulationError(
                f'next_step must be of type int, but is "{type(next_step)}" for '
                f'simulator "{sim.sid}"'
            )
        if next_step <= sim.last_step:
            raise SimulationError(
                f'next_step must be > last_step, but {next_step} <= {sim.last_step} '
                f'for simulator "{sim.sid}"'
            )

        if next_step not in sim.next_steps and next_step < world.until:
            heappush(sim.next_steps, next_step)

        sim.next_self_step = next_step

    if sim.type == 'time-based':
        return next_step
    else:
        if sim.next_steps:
            return min(sim.next_steps[0], max_advance + 1)
        else:
            return max_advance + 1


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
        delta = rt_passed - (rt_factor * sim.last_step)
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


async def get_outputs(world: World, sim: SimRunner, progress: int) -> int:
    """
    Wait for all required output data from a simulator *sim*.

    *world* is a mosaik :class:`~mosaik.scenario.World`.
    """
    sid = sim.sid
    outattr = world._df_outattr[sid]
    if outattr:
        sim.tqdm.set_postfix_str('get_data')
        data = await sim.proxy.get_data(outattr)

        if sim.type == 'time-based' and world._df_cache is not None:
            # Create a cache entry for every point in time the data is valid
            # for.
            for i in range(sim.last_step, progress):
                world._df_cache[i][sim.sid] = data
            sim.output_time = sim.last_step
        else:
            output_time: int
            output_time = sim.output_time = data.get('time', sim.last_step)  # type: ignore
            if sim.last_step > output_time:
                raise SimulationError(
                    'Output time (%s) is not >= time (%s) for simulator "%s"'
                    % (output_time, sim.last_step, sim.sid))

            progress = treat_cycling_output(world, sim, data, output_time, progress)

            if world._df_cache is not None:
                world._df_cache[sim.last_step][sim.sid] = data
                # TODO: Is it a problem if persistent data are also written?
                world._df_cache[output_time][sim.sid] = data

            for (src_eid, src_attr), destinations in sim.buffered_output.items():
                for dest_sid, dest_eid, dest_attr in destinations:
                    val = data.get(src_eid, {}).get(src_attr, SENTINEL)
                    if val is not SENTINEL:
                        world.sims[dest_sid].timed_input_buffer.add(
                            output_time, sid, src_eid, dest_eid, dest_attr, val)
        sim.data = data

    return progress


def treat_cycling_output(
    world: World,
    sim: SimRunner,
    data: OutputData,
    output_time: int,
    progress: int,
) -> int:
    """
    Check for each triggering cycle if the maximum number of iterations
    within the same time step has been reached. Also adjust the progress
    of *sim* if the cycle has been activated and could cause an earlier
    step then deduced in get_max_advance before."""
    for cycle in sim.trigger_cycles:
        max_iterations = world.max_loop_iterations
        for src_eid, src_attr in cycle.activators:
            if src_attr in data.get(src_eid, {}):
                if sim.last_step == cycle.time:
                    cycle.count += 1
                    if cycle.count > max_iterations:
                        raise SimulationError(
                            f"Loop {cycle.sids} reached maximal iteration "
                            f"count of {max_iterations}. "
                            "Adjust `max_loop_iterations` in the scenario "
                            "if needed."
                        )
                else:
                    cycle.time = output_time
                    cycle.count = 1
                # Check if output time could cause an earlier next step:
                cycle_progress = output_time + cycle.min_length
                if cycle_progress < progress:
                    progress = cycle_progress
                break

    return progress


def notify_dependencies(world: World, sim: SimRunner, progress: int) -> None:
    """
    Notify all simulators waiting for us.
    """
    sim.progress = progress

    # Notify simulators waiting for inputs from us.
    for dest_sim, edge in sim.successors.values():
        if not edge['wait_event'].is_set():
            weak_or_shifted = edge['time_shifted'] or edge['weak']
            if dest_sim.next_steps[0] - weak_or_shifted < progress:
                edge['wait_event'].set()
        for eid, attr in edge['trigger']:
            data_eid = sim.data.get(eid, {})
            if attr in data_eid:
                dest_input_time = sim.output_time + edge['time_shifted']
                dest_sim.schedule_step(dest_input_time)
                break  # Further triggering attributes would only schedule the same event

    # Notify simulators waiting for async. requests from us.
    for pre_sim, edge in sim.predecessors.values():
        if not edge['wait_async'].is_set() and pre_sim.next_steps[0] <= progress:
            edge['wait_async'].set()
        elif not edge['wait_lazy'].is_set():
            if not pre_sim.next_steps or pre_sim.next_steps[0] <= progress:
                edge['wait_lazy'].set()


def prune_dataflow_cache(world: World):
    """
    Prunes the dataflow cache.
    """
    min_cache_time = min(s.last_step for s in world.sims.values())
    for i in range(world._df_cache_min_time, min_cache_time):
        try:
            del world._df_cache[i]
        except KeyError:
            pass
    world._df_cache_min_time = min_cache_time


def get_progress(sims: Dict[SimId, SimRunner], until: int) -> float:
    """
    Return the current progress of the simulation in percent.
    """
    times = [sim.progress for sim in sims.values()]
    avg_time = sum(times) / len(times)
    return avg_time * 100 / until


def get_avg_progress(sims: Dict[SimId, SimRunner], until: int) -> int:
    """Get the average progress of all simulations (in time steps)."""
    times = [min(until, sim.progress + 1) for sim in sims.values()]
    return sum(times) // len(times)


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
        elif isim.sim_proc.done() or not isim.has_next_step.is_set():
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
        for pre_sim, edge in sim.predecessors.values():
            if not edge['wait_async'].is_set():
                edge['wait_async'].set()
            if not edge['wait_lazy'].is_set():
                edge['wait_lazy'].set()


def clear_wait_events(sim: SimRunner) -> None:
    """
    Clear/succeed all wait events *sim* is waiting for.
    """
    for _, edge in sim.predecessors.values():
        if not edge['wait_event'].is_set():
            edge['wait_event'].set()

    for _, edge in sim.successors.values():
        for wait_type in ['wait_lazy', 'wait_async']:
            if not edge[wait_type].is_set():
                edge[wait_type].set()


def clear_wait_events_dependencies(sim: SimRunner) -> None:
    """
    Clear/succeed all wait events over which other simulators are waiting for
    *sim*.
    """
    for _, edge in sim.successors.values():
        if not edge['wait_event'].is_set():
            edge['wait_event'].set()

    for _, edge in sim.predecessors.values():
        for wait_type in ['wait_lazy', 'wait_async']:
            if not edge[wait_type].is_set():
                edge[wait_type].set()
