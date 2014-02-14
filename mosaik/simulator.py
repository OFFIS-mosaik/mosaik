"""
This module is responsible for performing the simulation of a scenario.

"""
from collections import defaultdict

import simpy


def run(env, until):
    """Run the simulation for an :class:`~mosaik.scenario.Environment` until
    the simulation time *until* has been reached.

    Return the final simulation time.

    """
    senv = simpy.Environment()
    env.simpy_env = senv
    for sim in env.sims.values():
        senv.process(sim_process(env, sim, until))
    senv.run()


def sim_process(env, sim, until):
    """SimPy simulation process for a certain simulator *sim*.
    """
    while sim.next_step < until:
        yield step_required(env, sim)
        yield wait_for_dependencies(env, sim)
        input_data = get_input_data(env, sim)
        yield step(env, sim, input_data)
        yield get_outputs(env, sim)
        print('Progress: %.2f%%' % get_progress(env.sims, until))


def step_required(env, sim):
    """Return an :class:`~simpy.events.Event` that is triggered when *sim*
    needs to perform its next step.

    The event will already be triggered if the simulator is a "sink" (no other
    simulator depends on its outputs) or if another simulator is already
    waiting for it.

    *env* is a mosaik :class:`~mosaik.scenario.Environment`.

    """
    sim.step_required = env.simpy_env.event()
    dfg = env.df_graph
    sid = sim.sid
    if dfg.out_degree(sid) == 0 or any(('wait_event' in dfg[sid][s])
                                       for s in dfg.successors_iter(sid)):
        # A step is required if there are no outgoing edges or if one of the
        # edges had a "WaitEvent" attached.
        sim.step_required.succeed()
    # else:
    #   "wait_for_dependencies()" triggers the event when it creates a new
    #   "WaitEvent" for "sim".

    return sim.step_required


def wait_for_dependencies(env, sim):
    """Return an event (:class:`simpy.events.AllOf`) that is triggered when
    all dependencies can provide input data for *sim*.

    Also notify any simulator that is already waiting to perform its next step.

    *env* is a mosaik :class:`~mosaik.scenario.Environment`.

    """
    events = []
    t = sim.next_step
    for dep_sid in env.df_graph.predecessors_iter(sim.sid):
        dep = env.sims[dep_sid]
        if not (t in env._df_cache and dep_sid in env._df_cache[t]):
            # Wait for dep_sim if there's not data for it yet.
            evt = WaitEvent(env.simpy_env, t)
            events.append(evt)
            env.df_graph[dep_sid][sim.sid]['wait_event'] = evt

            if not dep.step_required.triggered:
                # Notify dependency that it needs to step now.
                dep.step_required.succeed()

    return env.simpy_env.all_of(events)


def get_input_data(env, sim):
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

    *env* is a mosaik :class:`~mosaik.scenario.Environment`.

    """
    input_data = {}
    for src_sid in env.df_graph.predecessors_iter(sim.sid):
        dataflows = env.df_graph[src_sid][sim.sid]['dataflows']
        for src_eid, dest_eid, attrs in dataflows:
            for src_attr, dest_attr in attrs:
                val = env._df_cache[sim.next_step][src_sid][src_eid][src_attr]
                input_data.setdefault(
                    dest_eid, {}).setdefault(dest_attr, []).append(val)

    return input_data


def step(env, sim, inputs):
    """Advance (step) a simulator *sim* with the given *inputs*. Return an
    event that is triggered when the step was performed.

    *inputs* is a dictionary, that maps entity IDs to data dictionaries which
    map attribute names to lists of values (see :func:`get_input_data()`).

    """
    sim.last_step = sim.next_step
    sim.next_step = sim.step(sim.next_step, inputs=inputs)

    # This event will be need when we send step() commands over network and
    # need to wait for a simulator's reply
    evt = env.simpy_env.event().succeed()
    return evt


def get_outputs(env, sim):
    """Get all required output data from a simulator *sim*, notify all
    simulators that are waiting for that data and prune the data flow cache.
    Return an event that is triggered when all output data is received.

    *env* is a mosaik :class:`~mosaik.scenario.Environment`.

    """
    sid = sim.sid
    outattr = env._df_outattr[sid]
    if outattr:
        # Create a cache entry for every point in time the data is valid for.
        data = sim.get_data(outattr)
        for i in range(sim.last_step, sim.next_step):
            env._df_cache[i][sim.sid] = data

    # Notify waiting simulators
    next_step = sim.next_step
    for suc_sid in env.df_graph.successors_iter(sid):
        edge = env.df_graph[sid][suc_sid]
        if 'wait_event' in edge and edge['wait_event'].time < next_step:
            edge.pop('wait_event').succeed()

    # Prune dataflow cache
    max_cache_time = min(s.next_step for s in env.sims.values())
    for cache_time in env._df_cache.keys():
        if cache_time < max_cache_time:
            del env._df_cache[cache_time]

    evt = env.simpy_env.event().succeed()
    return evt


def get_progress(sims, until):
    """Return the current progress of the simulation in percent."""
    times = [min(until, sim.next_step) for sim in sims.values()]
    avg_time = sum(times) / len(times)
    return avg_time * 100 / until


class WaitEvent(simpy.events.Event):
    """A normal event with an additional ``time`` attribute."""
    def __init__(self, env, time):
        super().__init__(env)
        self.time = time
        """The simulation time to which a simulator should advance."""
