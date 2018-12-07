"""
This module is responsible for performing the simulation of a scenario.
"""
from time import perf_counter

from mosaik.exceptions import SimulationError
from mosaik.simmanager import FULL_ID


def run(world, until, rt_factor=None, rt_strict=False):
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
                                          rt_strict))
        sim.sim_proc = process
        processes.append(process)

    yield env.all_of(processes)


def sim_process(world, sim, until, rt_factor, rt_strict):
    """
    SimPy simulation process for a certain simulator *sim*.
    """
    rt_start = perf_counter()

    try:
        keep_running = get_keep_running_func(world, sim, until)
        while keep_running():
            try:
                yield step_required(world, sim)
            except StopIteration:
                # We've been woken up by a terminating successor.
                # Check if we can also stop or need to keep running.
                continue

            yield wait_for_dependencies(world, sim)
            input_data = get_input_data(world, sim)
            yield from rt_sleep(rt_factor, rt_start, sim, world)
            yield from step(world, sim, input_data)
            rt_check(rt_factor, rt_start, rt_strict, sim)
            yield from get_outputs(world, sim)
            world.sim_progress = get_progress(world.sims, until)
            print('Progress: %.2f%%' % world.sim_progress, end='\r')

        # Before we stop, we wake up all dependencies who may be waiting for
        # us. They can then decide whether to also stop of if there's another
        # process left for which they need to provide data.
        for pre_sid in world.df_graph.predecessors(sim.sid):
            evt = world.sims[pre_sid].step_required
            if not evt.triggered:
                evt.fail(StopIteration())

    except ConnectionError as e:
        raise SimulationError('Simulator "%s" closed its connection.' %
                              sim.sid, e)


def get_keep_running_func(world, sim, until):
    """
    Return a function that the :func:`sim_process()` uses to determine
    when to stop.

    Depending on whether the process has any successors in the dataflow graph,
    the condition for when to stop differs.
    """

    def check_time():
        return sim.next_step < until

    if world.df_graph.out_degree(sim.sid) == 0:
        # If a sim process has no successors (no one needs its data), we just
        # need to check the time of its next step.
        keep_running = check_time
    else:
        # If there are any successors, we also check if they are still alive.
        # If all successors have finished, there's no need for us to continue
        # running.
        processes = [world.sims[suc_sid].sim_proc
                     for suc_sid in world.df_graph.successors(sim.sid)]

        def keep_running():
            return check_time() and not all(process.triggered
                                            for process in processes)

    return keep_running


def step_required(world, sim):
    """
    Return an :class:`~simpy.events.Event` that is triggered when *sim*
    needs to perform its next step.

    The event will already be triggered if the simulator is a "sink" (no other
    simulator depends on its outputs) or if another simulator is already
    waiting for it.

    *world* is a mosaik :class:`~mosaik.scenario.World`.
    """
    sim.step_required = world.env.event()
    dfg = world.df_graph
    sid = sim.sid

    if dfg.out_degree(sid) == 0 or any(('wait_event' in dfg[sid][s])
                                       for s in dfg.successors(sid)):
        # A step is required if there are no outgoing edges or if one of the
        sim.step_required.succeed()
    # else:
    #   "wait_for_dependencies()" triggers the event when it creates a new
    #   wait event for "sim".

    return sim.step_required


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
        if t in world._df_cache and dep_sid in world._df_cache[t]:
            continue

        # Wait for dep_sim if there's not data for it yet.
        evt = world.env.event()
        events.append(evt)
        world.df_graph[dep_sid][sim.sid]['wait_event'] = evt

        if not dep.step_required.triggered:
            dep.step_required.succeed()

    # Check if a successor may request data from us.
    # We cannot step any further until the successor may no longer require
    # data for [last_step, next_step) from us:
    for suc_sid in dfg.successors(sim.sid):
        suc = world.sims[suc_sid]
        if dfg[sim.sid][suc_sid]['async_requests'] and suc.next_step < t:
            evt = world.env.event()
            events.append(evt)
            world.df_graph[sim.sid][suc_sid]['wait_async'] = evt

    # Check if all predecessors with time-shifted input for us
    # have stepped for enough to provide the required input data:
    clg = world.shifted_graph
    for dep_sid in clg.predecessors(sim.sid):
        dep = world.sims[dep_sid]
        if dep.next_step < t:
            evt = world.env.event()
            events.append(evt)
            clg[dep_sid][sim.sid]['wait_shifted'] = evt

    return world.env.all_of(events)


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
    caches = [world._df_cache, world._shifted_cache]
    for i in range(len(graphs)):
        for src_sid in graphs[i].predecessors(sim.sid):
            dataflows = graphs[i][src_sid][sim.sid]['dataflows']
            for src_eid, dest_eid, attrs in dataflows:
                for src_attr, dest_attr in attrs:
                    v = caches[i][sim.next_step][src_sid][src_eid][src_attr]
                    vals = input_data.setdefault(dest_eid, {}) \
                        .setdefault(dest_attr, {})
                    vals[FULL_ID % (src_sid, src_eid)] = v

    return input_data


def step(world, sim, inputs):
    """
    Advance (step) a simulator *sim* with the given *inputs*. Return an
    event that is triggered when the step was performed.

    *inputs* is a dictionary, that maps entity IDs to data dictionaries which
    map attribute names to lists of values (see :func:`get_input_data()`).
    """
    sim.last_step = sim.next_step
    next_step = yield sim.proxy.step(sim.next_step, inputs)
    if type(next_step) != int:
        raise SimulationError('next_step must be of type int, but is "%s" for '
                              'simulator "%s"' % (type(next_step), sim.sid))
    if next_step <= sim.last_step:
        raise SimulationError('next_step must be > last_step, but %s <= %s '
                              'for simulator "%s"' %
                              (next_step, sim.last_step, sim.sid))
    sim.next_step = next_step


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
    # Create a cache entry for every point in time the data is valid for.
    for i in range(sim.last_step, sim.next_step):
        world._df_cache[i][sim.sid] = data
    # Create cache entries for the data from time-shifted connections.
    for i in range(sim.last_step, sim.next_step + 1):
        world._shifted_cache[i].setdefault(sim.sid, {})
        world._shifted_cache[i][sim.sid].update(data)

    next_step = sim.next_step

    # Notify simulators waiting for inputs from us.
    for suc_sid in world.df_graph.successors(sid):
        edge = world.df_graph[sid][suc_sid]
        dest_sim = world.sims[suc_sid]
        if 'wait_event' in edge and dest_sim.next_step < next_step:
            edge.pop('wait_event').succeed()

    # Notify simulators waiting for async. requests from us.
    for pre_sid in world.df_graph.predecessors(sid):
        edge = world.df_graph[pre_sid][sid]
        pre_sim = world.sims[pre_sid]
        if 'wait_async' in edge and pre_sim.next_step <= next_step:
            edge.pop('wait_async').succeed()

    # Notify simulators waiting for time-shifted input.
    for suc_sid in world.shifted_graph.successors(sid):
        edge = world.shifted_graph[sid][suc_sid]
        dest_sim = world.sims[suc_sid]
        if 'wait_shifted' in edge and dest_sim.next_step <= next_step:
            edge.pop('wait_shifted').succeed()

    # Prune dataflow cache
    min_cache_time = min(s.last_step for s in world.sims.values())
    for i in range(world._df_cache_min_time, min_cache_time):
        try:
            del world._df_cache[i]
            del world._shifted_cache[i]
        except KeyError:
            pass
    world._df_cache_min_time = min_cache_time


def get_progress(sims, until):
    """
    Return the current progress of the simulation in percent.
    """
    times = [min(until, sim.next_step) for sim in sims.values()]
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
