"""
This module is responsible for performing the simulation of a scenario.
"""
from __future__ import annotations

import asyncio
from heapq import heappop
from loguru import logger
from math import ceil
from time import perf_counter

from mosaik_api_v3 import InputData, SimId, Time

from mosaik.exceptions import SimulationError
from mosaik.internal_util import recursive_merge_all, recursive_merge_existing
from mosaik.simmanager import FULL_ID, SimRunner

from typing import TYPE_CHECKING, Any, Coroutine, Dict, List, Optional

from mosaik.tiered_time import TieredTime
if TYPE_CHECKING:
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

    setup_done_events: List[asyncio.Task[None]] = []
    for sim in world.sims.values():
        sim.tqdm.set_postfix_str('setup')
        # Send a setup_done event to all simulators
        setup_done_events.append(world.loop.create_task(sim.setup_done()))

    # Wait for all answers to be here
    await asyncio.gather(*setup_done_events)

    # Start simulator processes
    processes: List[asyncio.Task[None]] = []
    for sim in world.sims.values():
        process = world.loop.create_task(
            sim_process(world, sim, until, rt_factor, rt_strict, lazy_stepping),
            name=f"Runner for {sim.sid}"
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
        while await next_step_settled(sim, world):
            sim.tqdm.set_postfix_str('await input')
            await wait_for_dependencies(sim, lazy_stepping)
            sim.current_step = heappop(sim.next_steps)
            if sim.current_step != sim.progress.time:
                raise SimulationError(
                    f"Simulator {sim.sid} is trying to perform a step at time "
                    f"{sim.current_step}, but it has already progressed to time "
                    f"{sim.progress.time}."
                )
            if any(
                t >= world.max_loop_iterations for t in sim.current_step.tiers[1:]
            ):
                raise SimulationError(
                    f"Simulator {sim.sid} has performed a sub-step more than "
                    f"{world.max_loop_iterations} times. (The complete now is "
                    f"{sim.current_step}.) This might indicate that you have run into "
                    "an infinite loop. If not, you can increase max_loop_iterations to "
                    "get rid of this warning."
                )
            input_data = get_input_data(world, sim)
            max_advance = get_max_advance(world, sim, until)
            await step(world, sim, input_data, max_advance)
            rt_check(rt_factor, rt_start, rt_strict, sim)
            await get_outputs(world, sim)
            sim.current_step = None
            notify_dependencies(sim)
            # TODO: Reduce the number of sims that need to be advanced
            # (At least only to those that could potentially be
            # triggered by this step; maybe there's even a more clever
            # way.)
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


async def next_step_settled(sim: SimRunner, world: World) -> bool:
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
    while sim.progress.time.time < world.until:
        if sim.next_steps and sim.next_steps[0] == sim.progress.time:
            return True
        else:
            await_time = sim.next_steps[0] if sim.next_steps else TieredTime(world.until) + sim.from_world_time
            _, pending = await asyncio.wait(
                [
                    asyncio.create_task(sim.progress.has_reached(await_time)),
                    asyncio.create_task(sim.newer_step.wait()),
                ],
                return_when="FIRST_COMPLETED",
                timeout=world.rt_factor,
            )
            sim.newer_step.clear()
            for task in pending:
                task.cancel()
            if world.rt_factor:
                advance_progress(sim, world)
    return False


async def rt_sleep(
    sim: SimRunner,
    world: World
) -> None:
    """
    If in real-time mode, check if to sleep and do so if necessary.
    """
    if world.rt_factor:
        rt_passed = perf_counter() - sim.rt_start
        sleep = (world.rt_factor * sim.next_steps[0].time) - rt_passed
        if sleep > 0:
            sim.tqdm.set_postfix_str('sleeping')
            await asyncio.sleep(sleep)


async def wait_for_dependencies(
    sim: SimRunner,
    lazy_stepping: bool
) -> None:
    """
    Wait until all simulators that can provide input for this simulator have run for
    this step.

    Also notify any simulator that is already waiting to perform its next step.

    *world* is a mosaik :class:`~mosaik.scenario.World`.
    """
    futures: List[Coroutine[Any, Any, TieredTime]] = []
    next_step = sim.next_steps[0]

    for pre_sim, delay in sim.input_delays.items():
        # Wait for pre_sim if it hasn't progressed enough to provide
        # the input for our current step.
        futures.append(pre_sim.progress.has_passed(next_step, shift=delay))

    for suc_sim, adapt in sim.successors_to_wait_for.items():
        futures.append(suc_sim.progress.has_reached(next_step + adapt))
    if lazy_stepping:
        for suc_sim, adapt in sim.successors.items():
            futures.append(suc_sim.progress.has_reached(next_step + adapt))

    await asyncio.gather(*futures)


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
    # Input data starts with the data from set_data calls
    input_data = sim.inputs_from_set_data
    sim.inputs_from_set_data = {}
    # Merge the persistent inputs into the input data, adding keys as
    # necessary. mosaik controls three levels deep, all further levels
    # therefore should not be merged.
    recursive_merge_all(
        lambda attrs_new, attrs_old: recursive_merge_all(
            lambda data_new, data_old: recursive_merge_all(
                lambda val_new, val_old: val_new, data_new, data_old
            ),
            attrs_new,
            attrs_old,
        ),
        input_data,
        sim.persistent_inputs,
    )
    # Merge in pushed inputs from the timed input buffer
    input_data = sim.timed_input_buffer.get_input(input_data, sim.current_step.time)

    for (src_sim, delay), dataflows in sim.pulled_inputs.items():
        cache = src_sim.get_output_for(sim.current_step.time - delay.tiers[0])
        for (src_eid, src_attr), (dest_eid, dest_attr) in dataflows:
            try:
                val = cache[src_eid][src_attr]
            except KeyError:
                logger.warning(
                    f"Simulator {src_sim.sid}'s entity {src_eid} did not produce "
                    f"output on its persistent attribute {src_attr} during its last "
                    "step. However, this value is now required by simulator "
                    f"{sim.sid}. This usually results from attributes that are marked "
                    "persistent despite working like events. Supplying `None` for now. "
                    "This will be an error in future versions of mosaik."
                )
                val = None
            input_vals = input_data.setdefault(dest_eid, {}).setdefault(dest_attr, {})
            input_vals[FULL_ID % (src_sim.sid, src_eid)] = val

    # Merge the data back into the persistent inputs. Here, only keys
    # that already exist should be updated, as those are the persistent
    # attributes. (Adding others would make those persistent as well.)
    recursive_merge_existing(
        lambda attrs_old, attrs_new: recursive_merge_existing(
            lambda data_old, data_new: recursive_merge_existing(
                lambda val_old, val_new: val_new, data_old, data_new
            ),
            attrs_old,
            attrs_new,
        ),
        sim.persistent_inputs,
        input_data,
    )
    return input_data


def get_max_advance(world: World, sim: SimRunner, until: int) -> int:
    """
    Checks how far *sim* can safely advance its internal time during next step
    without causing a causality error.
    """
    ancs_next_steps: List[Time] = []
    for anc_sim, distance in sim.triggering_ancestors.items():
        if anc_sim.next_steps:
            ancs_next_steps.append((anc_sim.next_steps[0] + distance).time)

    own_next_step = [sim.next_steps[0].time] if sim.next_steps else []

    # The +1, -1 shenanigans exists due to how max_advance was
    # originally designed.
    return min([*ancs_next_steps, *own_next_step, until + 1]) - 1


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
        if not isinstance(next_step_time, int):
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
            next_step_tiered_time = TieredTime(next_step_time) + sim.from_world_time
            sim.schedule_step(next_step_tiered_time)
            sim.next_self_step = next_step_tiered_time

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
            output_tiered_time = sim.current_step
        else:
            output_tiered_time = TieredTime(output_time, *([0] * (len(sim.current_step) - 1)))
        sim.output_time = output_tiered_time
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
                for dest_sim, time_shift, (dest_eid, dest_attr) in destinations:
                    dest_sim.timed_input_buffer.add(
                        output_time + time_shift.tiers[0], sid, src_eid, dest_eid, dest_attr, val
                    )
            except KeyError:
                pass
        sim.data = data 


def notify_dependencies(sim: SimRunner) -> None:
    """
    Notify all simulators waiting for us.
    """
    for (eid, attr), triggered in sim.triggers.items():
        if attr in sim.data.get(eid, {}):
            for dest_sim, delay in triggered:
                dest_sim.schedule_step(sim.output_time + delay)


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
    times = [sim.progress.time.time for sim in sims.values()]
    avg_time = sum(times) / len(times)
    return avg_time * 100 / until


def get_avg_progress(sims: Dict[SimId, SimRunner], until: int) -> int:
    """Get the average progress of all simulations (in time steps)."""
    times = [min(until, sim.progress.time.time + 1) for sim in sims.values()]
    return sum(times) // len(times)


def advance_progress(sim: SimRunner, world: World):
    pre_sim_induced_progress: List[TieredTime] = [
        pre_sim.next_steps[0] + distance
        for pre_sim, distance in sim.triggering_ancestors.items()
        if pre_sim.next_steps
    ]

    next_step_progress: List[TieredTime] = [sim.next_steps[0]] if sim.next_steps else []
    current_step_prog = [sim.current_step] if sim.current_step else []
    if world.rt_factor:
        rt_passed = perf_counter() - sim.rt_start
        rt_progress = [TieredTime(ceil(rt_passed / world.rt_factor))]
    else:
        rt_progress = []
    new_progress = min([
        *pre_sim_induced_progress,
        *next_step_progress,
        *current_step_prog,
        *rt_progress,
        TieredTime(world.until) + sim.from_world_time,
    ])
    sim.progress.set(new_progress)
    sim.tqdm.update(new_progress.time - sim.tqdm.n)

