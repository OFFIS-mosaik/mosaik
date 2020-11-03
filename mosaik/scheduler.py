"""
This module is responsible for performing the simulation of a scenario.
"""
from heapq import heappush, heappop, heapreplace
import networkx as nx
from time import perf_counter
from simpy.exceptions import Interrupt

from mosaik.exceptions import (SimulationError, WakeUpException)
from mosaik.simmanager import FULL_ID


SENTINEL = object()


def run(world, until, rt_factor=None, rt_strict=False, print_progress=True):
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

    env = world.env

    setup_done_events = []
    for sim in world.sims.values():
        if sim.meta['api_version'] >= (2, 2):
            # setup_done() was added in API version 2.2:
            setup_done_events.append(sim.proxy.setup_done())

    yield env.all_of(setup_done_events)

    processes = []
    for sim in world.sims.values():
        process = env.process(sim_process(world, sim, until, rt_factor,
                                          rt_strict, print_progress))
        sim.sim_proc = process
        processes.append(process)

    yield env.all_of(processes)


def sim_process(world, sim, until, rt_factor, rt_strict, print_progress):
    """
    SimPy simulation process for a certain simulator *sim*.
    """
    rt_start = perf_counter()

    try:
        keep_running = get_keep_running_func(world, sim, until, rt_factor,
                                             rt_start)
        while keep_running():
            print(sim.sid, 'START LOOP')
            try:
                yield from has_next_step(world, sim)
            except WakeUpException:
                # We've been woken up by a terminating predecessor.
                # Check if we can also stop or need to keep running.
                continue
            print(f"{sim.sid} HAS NEXT STEP {sim.next_step}")
            sim.interruptable = True
            while True:
                try:
                    yield wait_for_dependencies(world, sim)
                    yield from rt_sleep(rt_factor, rt_start, sim, world)
                    print(sim.sid, 'WAITING DONE')
                    break
                except Interrupt as i:
                    print(sim.sid, 'INTERRUPTED')
                    assert i.cause == 'Earlier step'
                    sim.next_step = heapreplace(sim.next_steps, sim.next_step)
                    clear_wait_events(world, sim.sid)
                    continue
            sim.interruptable = False
            input_data = get_input_data(world, sim)

            max_advance = get_max_advance(world, sim, until)
            print('MAX ADV', max_advance)
            if (world.df_graph.in_degree(sim.sid) != 0 and input_data == {}
                    and sim.next_step != sim.next_self_step[0]):
                sim.output_time = sim.last_step = sim.next_step
                sim.progress_tmp = max_advance
                update_cache(world, sim)
            else:
                yield from step(world, sim, input_data, max_advance)
                rt_check(rt_factor, rt_start, rt_strict, sim)
                yield from get_outputs(world, sim)
            notify_dependencies(world, sim)
            prune_dataflow_cache(world)
            world.sim_progress = get_progress(world.sims, until)
            if print_progress:
                print('Progress: %.2f%%' % world.sim_progress, end='\r')
            print(sim.sid, 'END OF STEP', sim.last_step, sim.progress)

        print(sim.sid, 'DONE <<<<<<<<<<<<<<<<<')
        sim.progress_tmp = until
        update_cache(world, sim)
        sim.progress = until
        clear_wait_events_dependencies(world, sim.sid)
        # Before we stop, we wake up all dependencies who may be waiting for
        # us. They can then decide whether to also stop of if there's another
        # process left which might provide data.
        for suc_sid in world.trigger_graph.successors(sim.sid):
            if not world.sims[suc_sid].sim_proc.triggered:
                evt = world.sims[suc_sid].has_next_step
                if not evt.triggered:
                    world.sims[suc_sid].sim_proc.interrupt('Stopped simulator')

    except ConnectionError as e:
        raise SimulationError('Simulator "%s" closed its connection.' %
                              sim.sid, e)


def get_max_advance(world, sim, until):
    ancs_next_steps = []
    for anc_sid in nx.ancestors(world.trigger_graph, sim.sid):
        anc_sim = world.sims[anc_sid]
        if anc_sim.next_step:
            ancs_next_steps.append(anc_sim.next_step - 1)
        elif anc_sim.next_steps:
            ancs_next_steps.append(anc_sim.next_steps[0] - 1)

    if ancs_next_steps:
        max_advance = min(ancs_next_steps)
    else:
        max_advance = until

    if sim.next_steps:
        max_advance = min(sim.next_steps[0], max_advance)

    return max_advance


def get_keep_running_func(world, sim, until, rt_factor, rt_start):
    """
    Return a function that the :func:`sim_process()` uses to determine
    when to stop.

    Depending on whether the process has any successors in the dataflow graph,
    the condition for when to stop differs.
    """
    if world.trigger_graph.in_degree(sim.sid) == 0:
        def check_time():
            return sim.progress + 1 < until
    else:
        def check_time():
            return sim.progress < until

    check_functions = [check_time]

    if world.df_graph.out_degree(sim.sid) != 0:
        # If there are any successors, we check if they are still alive.
        # If all successors have finished, there's no need for us to continue
        # running.
        processes = [world.sims[suc_sid].sim_proc for suc_sid in
                     world.df_graph.successors(sim.sid)]

        def check_successors():
            return not all(process.triggered for process in processes)

        check_functions.append(check_successors)

    if sim.meta['type'] != 'discrete-time':
        # If we are not self-stepped we can stop if all predecessors have
        # stopped and there's no step left.
        # Unless we are running in real-time mode, then we have to wait until
        # the total wall-clock time has passed.
        if not rt_factor:
            pre_procs = [world.sims[pre_sid].sim_proc for pre_sid in
                         world.trigger_graph.predecessors(sim.sid)]

            def check_trigger():
                return sim.next_steps or not all(process.triggered
                                                for process in pre_procs)
        else:
            def check_trigger():
                return sim.next_steps or \
                    (perf_counter() - rt_start < rt_factor * until)

        check_functions.append(check_trigger)

    def keep_running():
        return all([f() for f in check_functions])

    return keep_running


def get_next_step(sim):
    next_step = heappop(sim.next_steps) if sim.next_steps else None
    if next_step:
        next_step = max(next_step, sim.progress)

    return next_step


def has_next_step(world, sim):
    """
    Return an :class:`~simpy.events.Event` that is triggered when *sim*
    has a next step.

    *world* is a mosaik :class:`~mosaik.scenario.World`.
    """
    sim.has_next_step = world.env.event()
    next_step = get_next_step(sim)

    if next_step is not None:
        sim.has_next_step.succeed()
        yield sim.has_next_step
    else:
        try:
            yield sim.has_next_step
        except Interrupt:
            raise WakeUpException

        next_step = get_next_step(sim)

    sim.next_step = next_step


def wait_for_dependencies(world, sim):
    """
    Return an event (:class:`simpy.events.AllOf`) that is triggered when
    all dependencies can provide input data for *sim*.

    Also notify any simulator that is already waiting to perform its next step.

    *world* is a mosaik :class:`~mosaik.scenario.World`.
    """
    events = []
    t = sim.next_step
    dfg = world.df_graph

    # Check if all predecessors have stepped far enough
    # to provide the required input data for us:
    for dep_sid in dfg.predecessors(sim.sid):
        dep = world.sims[dep_sid]
        edge = dfg[dep_sid][sim.sid]
        # Wait for dep_sim if it hasn't progressed until actual time step:
        weak_or_shifted = edge['time_shifted'] or edge['weak']
        if dep.progress + weak_or_shifted < t:
            evt = world.env.event()
            events.append(evt)
            edge['wait_event'] = evt
            print(sim.sid, 'WAITS FOR', dep_sid)
            # To avoid deadlocks:
            if 'wait_lazy_or_async' in edge and dep.next_step <= t:
                edge.pop('wait_lazy_or_async').succeed()

    # Check if a successor may request data from us.
    # We cannot step any further until the successor may no longer require
    # data for [last_step, next_step) from us:
    for suc_sid in dfg.successors(sim.sid):
        suc = world.sims[suc_sid]
        if suc.progress + 1 < t:
            evt = world.env.event()
            events.append(evt)
            world.df_graph[sim.sid][suc_sid]['wait_lazy_or_async'] = evt

    wait_events = world.env.all_of(events)
    sim.wait_events = wait_events

    return wait_events


def get_input_data(world, sim):
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
    input_data = sim.input_buffer
    sim.input_buffer = {}
    df_graph = world.df_graph

    for src_sid in df_graph.predecessors(sim.sid):
        t = sim.next_step - df_graph[src_sid][sim.sid]['time_shifted']
        dataflows = df_graph[src_sid][sim.sid]['dataflows']
        for src_eid, dest_eid, attrs in dataflows:
            for src_attr, dest_attr in attrs:
                v = world._df_cache[t].get(src_sid, {}).get(src_eid, {})\
                    .get(src_attr, SENTINEL)
                if v is not SENTINEL:
                    vals = input_data.setdefault(dest_eid, {}) \
                        .setdefault(dest_attr, {})
                    vals[FULL_ID % (src_sid, src_eid)] = v

    return input_data


def step(world, sim, inputs, max_advance):
    """
    Advance (step) a simulator *sim* with the given *inputs*. Return an
    event that is triggered when the step was performed.

    *inputs* is a dictionary, that maps entity IDs to data dictionaries which
    map attribute names to lists of values (see :func:`get_input_data()`).
    """
    sim.last_step = sim.next_step
    step_return = yield sim.proxy.step(sim.next_step, inputs)
    if isinstance(step_return, dict):
        next_step = step_return.get('next_step', None)
    elif isinstance(step_return, int) or step_return is None:
        next_step = step_return

    if next_step is not None:
        if type(next_step) != int:
            raise SimulationError('next_step must be of type int, but is "%s" '
                                  'for simulator "%s"' % (
                                                    type(next_step), sim.sid))
        if next_step <= sim.last_step:
            raise SimulationError('next_step must be > last_step, but %s <= %s'
                                  ' for simulator "%s"' %
                                  (next_step, sim.last_step, sim.sid))

        if next_step not in sim.next_steps and next_step < world.until:
            heappush(sim.next_steps, next_step)

    if sim.meta['type'] == 'discrete-time':
        sim.progress_tmp = next_step - 1
    else:
        assert max_advance >= sim.last_step
        requested_progress = step_return.get('progress', None)
        if requested_progress:
            sim.progress_tmp = requested_progress

            if sim.last_step > requested_progress > max_advance:
                raise SimulationError('progress (%s) is not >= time (%s) and '
                                      '<= max_advance (%s) for simulator "%s"'
                                      % (requested_progress, sim.last_step,
                                         max_advance, sim.sid))

        elif sim.next_steps:
            sim.progress_tmp = min(sim.next_steps[0] - 1, max_advance)
        else:
            sim.progress_tmp = max_advance

    sim.next_step = None
    if next_step is not None:
        sim.next_self_step = (next_step, sim.last_step)


def get_outputs(world, sim):
    """
    Get all required output data from a simulator *sim*.
    Yield an event that is triggered when all output data is received.

    *world* is a mosaik :class:`~mosaik.scenario.World`.
    """
    sid = sim.sid
    outattr = world._df_outattr[sid]
    if outattr:
        data = yield sim.proxy.get_data(outattr)

        if sim.meta['type'] == 'discrete-time':
            # Create a cache entry for every point in time the data is valid
            # for.
            for i in range(sim.last_step, sim.progress_tmp + 1):
                world._df_cache[i][sim.sid] = data
            sim.output_time = sim.last_step
        else:
            output_time = sim.output_time = data.get('time', sim.last_step)
            if sim.last_step > output_time:
                raise SimulationError(
                    'Output time (%s) is not >= time (%s) for simulator "%s"'
                    % (output_time, sim.last_step, sim.sid))

            for cycle in sim.trigger_cycles:
                for src_eid, src_attr in cycle['activators']:
                    if src_attr in data.get(src_eid, {}):
                        if output_time < sim.progress_tmp:
                            sim.progress_tmp = output_time

            persistent_attrs = world.persistent_outattrs[sid]
            if persistent_attrs:
                pers_data = {eid: {attr: data[eid][attr]}
                             for eid, attrs in persistent_attrs.items()
                             for attr in attrs}
                i_start = (sim.progress + 1 if sim.last_step > sim.progress
                           else sim.last_step)
                for i in range(i_start, sim.progress_tmp + 1):
                    if sim.sid not in world._df_cache.setdefault(i, {}):
                        world._df_cache[i][sim.sid] = pers_data
                    else:
                        world._df_cache[i][sim.sid].update(pers_data)

            world._df_cache[output_time][sim.sid] = data

            for (src_eid, src_attr), (dest_sid, dest_eid, dest_attr) in sim.buffered_output.items():
                val = data.get(src_eid, {}).get(src_attr, SENTINEL)
                if val is not SENTINEL:
                    world.sims[dest_sid].input_buffer.setdefault(dest_eid,
                                                                 {}).setdefault(
                        dest_attr, {})[FULL_ID % (sim.sid, src_eid)] = val


def update_cache(world, sim):
    """

    """
    persistent_attrs = world.persistent_outattrs[sim.sid]
    if persistent_attrs:
        data = world._df_cache[sim.progress][sim.sid]
        pers_data = {eid: {attr: data[eid][attr]}
                     for eid, attrs in persistent_attrs.items()
                     for attr in attrs}
        for i in range(sim.progress + 1, sim.progress_tmp + 1):
            world._df_cache[i][sim.sid] = pers_data


def notify_dependencies(world, sim):
    """
    Notify all simulators waiting for us
    """
    sid = sim.sid
    progress = sim.progress = sim.progress_tmp

    # Notify simulators waiting for inputs from us.
    for suc_sid in world.df_graph.successors(sid):
        edge = world.df_graph[sid][suc_sid]
        dest_sim = world.sims[suc_sid]
        if ('wait_event' in edge
                and (dest_sim.next_step <= progress + (edge['time_shifted']
                                                       or edge['weak']))):
            edge.pop('wait_event').succeed()
        if (edge['trigger']
                and sim.output_time not in dest_sim.next_steps
                + [dest_sim.next_step]
                and sim.output_time < world.until):
            heappush(dest_sim.next_steps, sim.output_time)
            if not dest_sim.has_next_step.triggered:
                dest_sim.has_next_step.succeed()
            elif dest_sim.interruptable and \
                    dest_sim.progress <= sim.output_time < dest_sim.next_step:
                dest_sim.sim_proc.interrupt('Earlier step')

    # Notify simulators waiting for async. requests from us.
    for pre_sid in world.df_graph.predecessors(sid):
        edge = world.df_graph[pre_sid][sid]
        pre_sim = world.sims[pre_sid]
        if 'wait_lazy_or_async' in edge and (
                not sim.next_steps or pre_sim.next_step <= progress + 1):
            edge.pop('wait_lazy_or_async').succeed()


def prune_dataflow_cache(world):
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


def get_progress(sims, until):
    """
    Return the current progress of the simulation in percent.
    """
    times = [min(until, sim.progress + 1) for sim in sims.values()]
    avg_time = sum(times) / len(times)
    return avg_time * 100 / until


def rt_sleep(rt_factor, rt_start, sim, world):
    """
    If in real-time mode, check if to sleep and do so if necessary.
    """
    if rt_factor:
        rt_passed = perf_counter() - rt_start
        sleep = (rt_factor * sim.next_step) - rt_passed
        if sleep > 0:
            yield world.env.timeout(sleep)


def rt_check(rt_factor, rt_start, rt_strict, sim):
    """
    Check if simulation is fast enough for a given real-time factor.
    """
    if rt_factor:
        rt_passed = perf_counter() - rt_start
        delta = rt_passed - (rt_factor * sim.last_step)
        if delta > 0:
            if rt_strict:
                raise RuntimeError('Simulation too slow for real-time factor '
                                   '%s' % rt_factor)
            else:
                print('Simulation too slow for real-time factor %s - %ss '
                      'behind time.' % (rt_factor, delta))


def clear_wait_events(world, sid):
    for pre_sid in world.df_graph.predecessors(sid):
        edge = world.df_graph[pre_sid][sid]
        if 'wait_event' in edge:
            edge.pop('wait_event').succeed()

    for suc_sid in world.df_graph.successors(sid):
        edge = world.df_graph[sid][suc_sid]
        if 'wait_lazy_or_async' in edge:
            edge.pop('wait_lazy_or_async').succeed()


def clear_wait_events_dependencies(world, sid):
    for suc_sid in world.df_graph.successors(sid):
        edge = world.df_graph[sid][suc_sid]
        if 'wait_event' in edge:
            edge.pop('wait_event').succeed()

    for pre_sid in world.df_graph.predecessors(sid):
        edge = world.df_graph[pre_sid][sid]
        if 'wait_lazy_or_async' in edge:
            edge.pop('wait_lazy_or_async').succeed()
