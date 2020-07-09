"""
This module is responsible for performing the simulation of a scenario.
"""
from time import perf_counter
from simpy.exceptions import Interrupt

from mosaik.exceptions import (SimulationError, NoStepsException,
                               WakeUpException)
from mosaik.simmanager import FULL_ID


SENTINEL = object()


def run(world, until, rt_factor=None, rt_strict=False, print_progress=True,
        lazy_stepping=True):
    """
    Run the simulation for a :class:`~mosaik.scenario.World` until
    the simulation time *until* has been reached.

    Return the final simulation time.

    See :meth:`mosaik.scenario.World.run()` for a detailed description of the
    *rt_factor* and *rt_strict* arguments.
    """
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
                                    rt_strict, print_progress, lazy_stepping))
        sim.sim_proc = process
        processes.append(process)

    yield env.all_of(processes)


def sim_process(world, sim, until, rt_factor, rt_strict, print_progress,
                lazy_stepping):
    """
    SimPy simulation process for a certain simulator *sim*.
    """
    rt_start = perf_counter()

    try:
        keep_running = get_keep_running_func(world, sim, until, rt_factor,
                                             rt_start)
        while keep_running():
            try:
                yield from has_next_step(world, sim)
            except WakeUpException:
                # We've been woken up by a terminating predecessor.
                # Check if we can also stop or need to keep running.
                continue
            except NoStepsException:
                break
            while True:
                try:
                    yield wait_for_dependencies(world, sim, lazy_stepping)
                    break
                except Interrupt as i:
                    sim.next_step = get_next_step(sim)
                    clear_wait_events(world, sim.sid)
                    continue
            input_data = get_input_data(world, sim)
            rt_check(rt_factor, rt_start, rt_strict, sim)
            yield from rt_sleep(rt_factor, rt_start, sim, world)
            yield from step(world, sim, input_data)
            yield from get_outputs(world, sim)
            world.sim_progress = get_progress(world.sims, until)
            if print_progress:
                print('Progress: %.2f%%' % world.sim_progress, end='\r')

        # Before we stop, we wake up all dependencies who may be waiting for
        # us. They can then decide whether to also stop of if there's another
        # process left which might provide data.
        for suc_sid in world.df_graph.successors(sim.sid):
            evt = world.sims[suc_sid].has_next_step
            if not evt.triggered:
                evt.fail(StopIteration())

    except ConnectionError as e:
        raise SimulationError('Simulator "%s" closed its connection.' %
                              sim.sid, e)


def get_keep_running_func(world, sim, until, rt_factor, rt_start):
    """
    Return a function that the :func:`sim_process()` uses to determine
    when to stop.

    Depending on whether the process has any successors in the dataflow graph,
    the condition for when to stop differs.
    """

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

    if world.df_graph.in_degree(sim.sid) == 0:
        # If there are no predecessors, we can stop if there's no new self_step
        # and we are not running in real-time mode or the total wall-clock time
        # has passed.
        if not rt_factor:
            def check_selfstep():
                return sim.next_self_step is not None
        else:
            def check_selfstep():
                return sim.next_self_step is not None or \
                    (perf_counter() - rt_start < rt_factor * until)

        check_functions.append(check_selfstep)

    def keep_running():
        return all([f() for f in check_functions])

    return keep_running


def get_next_step(sim):
    next_step = sim.event_buffer.peek_next_time()
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
        no_steps = check_resolve_deadlocks(world)
        if no_steps:
            raise NoStepsException
        try:
            yield sim.has_next_step
        except StopIteration:
            raise WakeUpException

        next_input_message = sim.event_buffer.peek_next_time()
        next_step = max(next_input_message, sim.progress)

    sim.next_step = next_step


def wait_for_dependencies(world, sim, lazy_stepping):
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
        if dep.progress < t + int(not dfg[dep_sid][sim.sid]['weak']):
            # Wait for dep_sim if it hasn't progressed until actual time step
            evt = world.env.event()
            events.append(evt)
            world.df_graph[dep_sid][sim.sid]['wait_event'] = evt

    # Check if we have to wait lazily or a successor may request data from us.
    # We cannot step any further until the successor has progressed at least
    # until next_step or may no longer require data for [last_step, next_step)
    # from us:
    for suc_sid in dfg.successors(sim.sid):
        suc = world.sims[suc_sid]
        if (lazy_stepping or dfg[sim.sid][suc_sid]['async_requests']) and suc.progress < t:
            evt = world.env.event()
            events.append(evt)
            world.df_graph[sim.sid][suc_sid]['wait_lazy_or_async'] = evt

    # Check if all predecessors with time-shifted input for us
    # have stepped for enough to provide the required input data:
    clg = world.shifted_graph
    for dep_sid in clg.predecessors(sim.sid):
        dep = world.sims[dep_sid]
        if dep.progress < t:
            evt = world.env.event()
            events.append(evt)
            clg[dep_sid][sim.sid]['wait_shifted'] = evt

    wait_events = world.env.all_of(events)
    sim.wait_events = wait_events

    check_resolve_deadlocks(world)

    return wait_events


def check_resolve_deadlocks(world):
    for isim in world.sims.values():
        if not isim.has_next_step:
            # isim hasn't executed `has_next_step` yet and will perform
            # a deadlock check again if necessary.
            return
        elif not isim.has_next_step.triggered:
            continue
        if not isim.wait_events or isim.wait_events.triggered:
            # isim hasn't executed `wait_for_dependencies` yet and will perform
            # a deadlock check again if necessary or is not waiting.
            return

    # This part will only be reached if all simulators either have no next step
    # or are waiting for dependencies.
    next_steps = [isim.next_step for isim in world.sims.values()
                  if isim.next_step is not None]
    if not next_steps:
        return True

    min_next_step = min(next_steps)

    next_waiting_sims = [(world.sim_ranks[isid], isid)
                         for isid, isim in world.sims.items()
                         if isim.next_step == min_next_step]
    next_sim = min(next_waiting_sims)[1]

    clear_wait_events(world, next_sim)


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
    graphs = [world.df_graph, world.shifted_graph]
    for i, graph in enumerate(graphs):
        t = sim.next_step - i  # -1 for shifted connections
        for src_sid in graph.predecessors(sim.sid):
            dataflows = graph[src_sid][sim.sid]['dataflows']
            for src_eid, dest_eid, attrs in dataflows:
                for src_attr, dest_attr in attrs:
                    v = world._df_cache[t][src_sid][src_eid][src_attr]
                    vals = input_data.setdefault(dest_eid, {}) \
                        .setdefault(dest_attr, {})
                    vals[FULL_ID % (src_sid, src_eid)] = v

    input_messages = sim.event_buffer.get_messages(sim.next_step)
    recursive_update(input_data, input_messages)

    return input_data


def recursive_update(d, u):
    for k, v in u.items():
        if isinstance(v, dict):
            d[k] = recursive_update(d.get(k, {}), v)
        else:
            d[k] = v
    return d


def step(world, sim, inputs):
    """
    Advance (step) a simulator *sim* with the given *inputs*. Return an
    event that is triggered when the step was performed.

    *inputs* is a dictionary, that maps entity IDs to data dictionaries which
    map attribute names to lists of values (see :func:`get_input_data()`).
    """
    sim.last_step = sim.next_step
    next_step = yield sim.proxy.step(sim.next_step, inputs)
    if next_step is not None:
        if type(next_step) != int:
            raise SimulationError('next_step must be of type int, but is "%s" for '
                                  'simulator "%s"' % (type(next_step), sim.sid))
        if next_step <= sim.last_step:
            raise SimulationError('next_step must be > last_step, but %s <= %s '
                                  'for simulator "%s"' %
                                  (next_step, sim.last_step, sim.sid))

        sim.progress_tmp = next_step
    else:
        preds_progresses = [world.sims[pre_sid].progress for pre_sid in
                              world.df_graph.predecessors(sim.sid)]
        if preds_progresses:
            preds_progress = min(preds_progresses)
            sim.progress_tmp = max(preds_progress, sim.last_step + 1)
        else:
            sim.progress_tmp = sim.last_step + 1

    sim.next_step = None
    sim.next_self_step = next_step
    if next_step is not None:
        sim.event_buffer.add_self_step(next_step)


def get_outputs(world, sim):
    """
    Get all required output data from a simulator *sim*, notify all
    simulators that are waiting for that data and prune the data flow cache.
    Return an event that is triggered when all output data is received.

    *world* is a mosaik :class:`~mosaik.scenario.World`.
    """
    sid = sim.sid
    outattr = world._df_outattr[sid]
    if outattr:
        data = yield sim.proxy.get_data(outattr)
    else:
        data = {}  # Just to indicate that the step/get is completely done.

    graphs = [world.df_graph, world.shifted_graph]
    for i, graph in enumerate(graphs):
        message_time = sim.last_step + i  # +1 for shifted connections
        for dest_sid in graph.successors(sid):
            messageflows = graph[sid][dest_sid]['messageflows']
            if messageflows:
                event_buffer = world.sims[dest_sid].event_buffer
                step_added = False
                for src_eid, dest_eid, messages in messageflows:
                    for src_msg, dest_msg in messages:
                        content = data.get(src_eid, {}).get(src_msg, SENTINEL)
                        if content is not SENTINEL:
                            event_buffer.add(message_time, sid, src_eid,
                                               src_msg, content)
                            step_added = True

                if step_added and not world.sims[dest_sid].has_next_step.triggered:
                    world.sims[dest_sid].has_next_step.succeed()
                if step_added and world.sims[dest_sid].wait_events\
                        and not world.sims[dest_sid].wait_events.triggered\
                        and message_time < world.sims[dest_sid].next_step\
                        and message_time >= world.sims[dest_sid].progress:
                    world.sims[dest_sid].sim_proc.interrupt('Earlier step')

    # Create a cache entry for every point in time the data is valid for.
    for i in range(sim.last_step, sim.progress_tmp):
        world._df_cache[i][sim.sid] = data

    progress = sim.progress = sim.progress_tmp

    # Notify simulators waiting for inputs from us.
    for suc_sid in world.df_graph.successors(sid):
        edge = world.df_graph[sid][suc_sid]
        dest_sim = world.sims[suc_sid]
        if 'wait_event' in edge and dest_sim.next_step < progress + world.df_graph[sid][suc_sid]['weak']:
            edge.pop('wait_event').succeed()

    # Notify simulators waiting for async. requests from us.
    for pre_sid in world.df_graph.predecessors(sid):
        edge = world.df_graph[pre_sid][sid]
        pre_sim = world.sims[pre_sid]
        if 'wait_lazy_or_async' in edge and pre_sim.next_step <= progress:
            edge.pop('wait_lazy_or_async').succeed()

    # Notify simulators waiting for time-shifted input.
    for suc_sid in world.shifted_graph.successors(sid):
        edge = world.shifted_graph[sid][suc_sid]
        dest_sim = world.sims[suc_sid]
        if 'wait_shifted' in edge and dest_sim.next_step <= progress:
            edge.pop('wait_shifted').succeed()

    # Prune dataflow cache
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
    times = [min(until, sim.progress) for sim in sims.values()]
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
        delta = rt_passed - (rt_factor * sim.next_step)
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

    for pre_sid in world.shifted_graph.predecessors(sid):
        edge = world.shifted_graph[pre_sid][sid]
        if 'wait_shifted' in edge:
            edge.pop('wait_shifted').succeed()

    for suc_sid in world.df_graph.successors(sid):
        edge = world.df_graph[sid][suc_sid]
        if 'wait_lazy_or_async' in edge:
            edge.pop('wait_lazy_or_async').succeed()