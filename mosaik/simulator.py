"""
This module is responsible for performing the simulation of a scenario.

"""
import simpy


def run(world, until):
    """Run the simulation for a :class:`~mosaik.scenario.World` until
    the simulation time *until* has been reached.

    Return the final simulation time.

    """
    env = world.env
    procs = []
    for sim in world.sims.values():
        proc = env.process(sim_process(world, sim, until))
        sim.sim_proc = proc
        procs.append(proc)

    env.run(until=env.all_of(procs))


def sim_process(world, sim, until):
    """SimPy simulation process for a certain simulator *sim*."""
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
        yield from step(world, sim, input_data)
        yield from get_outputs(world, sim)
        world.sim_progress = get_progress(world.sims, until)
        print('Progress: %.2f%%' % world.sim_progress, end='\r')

    # Before we stop, we wake up all dependencies who may be waiting for us.
    # They can then decide whether to also stop of if there's another process
    # left for which they need to provide data.
    for pre_sid in world.df_graph.predecessors_iter(sim.sid):
        evt = world.sims[pre_sid].step_required
        if not evt.triggered:
            evt.fail(StopIteration())


def get_keep_running_func(world, sim, until):
    """Return a function that the :func:`sim_process()` uses to determine
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
        procs = [world.sims[suc_sid].sim_proc
                 for suc_sid in world.df_graph.successors_iter(sim.sid)]

        def keep_running():
            return check_time() and not all(proc.triggered for proc in procs)

    return keep_running


def step_required(world, sim):
    """Return an :class:`~simpy.events.Event` that is triggered when *sim*
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
                                       for s in dfg.successors_iter(sid)):
        # A step is required if there are no outgoing edges or if one of the
        sim.step_required.succeed()
    # else:
    #   "wait_for_dependencies()" triggers the event when it creates a new
    #   "WaitEvent" for "sim".

    return sim.step_required


def wait_for_dependencies(world, sim):
    """Return an event (:class:`simpy.events.AllOf`) that is triggered when
    all dependencies can provide input data for *sim*.

    Also notify any simulator that is already waiting to perform its next step.

    *world* is a mosaik :class:`~mosaik.scenario.World`.

    """
    events = []
    t = sim.next_step
    for dep_sid in world.df_graph.predecessors_iter(sim.sid):
        dep = world.sims[dep_sid]
        if not (t in world._df_cache and dep_sid in world._df_cache[t]):
            # Wait for dep_sim if there's not data for it yet.
            evt = WaitEvent(world.env, t)
            events.append(evt)
            world.df_graph[dep_sid][sim.sid]['wait_event'] = evt

            if not dep.step_required.triggered:
                dep.step_required.succeed()

    return world.env.all_of(events)


def get_input_data(world, sim):
    """Return a dictionary with the input data for *sim*.

    The dict will look like::

        {
            'eid': {
                'attrname': [val_0, ..., val_n],
                ...
            },
            ...
        }

    For every entity, there is an entry in the dict and each entry is itself
    a dict with attributes and a list of values. This is, because we may have
    inputs from multiple simulators (e.g., different consumers that provide
    loads for a node in a power grid) and cannot know how to aggreate that data
    (sum, max, ...?).

    *world* is a mosaik :class:`~mosaik.scenario.World`.

    """
    input_data = {}
    for src_sid in world.df_graph.predecessors_iter(sim.sid):
        dataflows = world.df_graph[src_sid][sim.sid]['dataflows']
        for src_eid, dest_eid, attrs in dataflows:
            for src_attr, dest_attr in attrs:
                v = world._df_cache[sim.next_step][src_sid][src_eid][src_attr]
                input_data.setdefault(
                    dest_eid, {}).setdefault(dest_attr, []).append(v)

    return input_data


def step(world, sim, inputs):
    """Advance (step) a simulator *sim* with the given *inputs*. Return an
    event that is triggered when the step was performed.

    *inputs* is a dictionary, that maps entity IDs to data dictionaries which
    map attribute names to lists of values (see :func:`get_input_data()`).

    """
    sim.last_step = sim.next_step
    sim.next_step = yield sim.step(sim.next_step, inputs)


def get_outputs(world, sim):
    """Get all required output data from a simulator *sim*, notify all
    simulators that are waiting for that data and prune the data flow cache.
    Return an event that is triggered when all output data is received.

    *world* is a mosaik :class:`~mosaik.scenario.World`.

    """
    sid = sim.sid
    outattr = world._df_outattr[sid]
    if outattr:
        # Create a cache entry for every point in time the data is valid for.
        data = yield sim.get_data(outattr)
        for i in range(sim.last_step, sim.next_step):
            world._df_cache[i][sim.sid] = data

    # Notify waiting simulators
    next_step = sim.next_step
    for suc_sid in world.df_graph.successors_iter(sid):
        edge = world.df_graph[sid][suc_sid]
        if 'wait_event' in edge and edge['wait_event'].time < next_step:
            edge.pop('wait_event').succeed()

    # Prune dataflow cache
    max_cache_time = min(s.next_step for s in world.sims.values())
    for cache_time in world._df_cache.keys():
        if cache_time < max_cache_time:
            del world._df_cache[cache_time]


def get_progress(sims, until):
    """Return the current progress of the simulation in percent."""
    times = [min(until, sim.next_step) for sim in sims.values()]
    avg_time = sum(times) / len(times)
    return avg_time * 100 / until


class WaitEvent(simpy.events.Event):
    """A normal event with an additional ``time`` attribute."""
    def __init__(self, world, time):
        super().__init__(world)
        self.time = time
        """The simulation time to which a simulator should advance."""
