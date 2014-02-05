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
    while sim.time < until:
        yield wait_for_dependencies(env, sim)
        input_data = get_input_data(env, sim)
        yield step(env, sim, input_data)
        yield get_outputs(env, sim)
        print('Progress: %5.3f%%' % get_progress(env.sims, until))


def wait_for_dependencies(env, sim):
    events = []
    for dep_sid in env.df_graph.predecessors_iter(sim.sid):
        if env.sims[dep_sid].time < sim.time:
            evt = env.simpy_env.event()
            events.append(evt)

            env.df_graph[dep_sid][sim.sid]['wait_evt'] = evt
            env.df_graph[dep_sid][sim.sid]['wait_time'] = sim.time

    return env.simpy_env.all_of(events)


def get_input_data(env, sim):
    input_data = defaultdict(lambda: defaultdict(list))
    for src_sid in env.df_graph.predecessors_iter(sim.sid):
        dataflows = env.df_graph[src_sid][sim.sid]['dataflows']
        for src_eid, dest_eid, attrs in dataflows:
            for src_attr, dest_attr in attrs:
                val = env._df_cache[sim.time][src_sid][src_eid][src_attr]
                input_data[dest_eid][dest_attr].append(val)

    return input_data


def step(env, sim, inputs):
    # TODO: If a simulator had no dependencies it could theoretically run
    # until the simulation end while other simulators are still way behind.
    # If theses simulators need data from it, we'd have to cache the the
    # simulators data for the complete simulation time which may require
    # lots of memory. Furthermore, if we allowed simulators (like FMI) to
    # rollback, they also shouldn't run until the simulation end or we would
    # not be able to roll them back (because we can only do a rollback until
    # we got data from them). So we need a way to slow down faster simulators
    # so that they only run until they reach a max. t or a sync. point.
    sim.time = sim.next_time
    time = sim.step(sim.time, inputs=inputs)
    sim.next_time = time

    evt = env.simpy_env.event().succeed()

    for suc_sid in env.df_graph.successors_iter(sim.sid):
        edge = env.df_graph[sim.sid][suc_sid]
        if 'wait_evt' in edge and edge['wait_time'] < time:
            edge.pop('wait_evt').succeed()

    return evt


def get_outputs(env, sim):
    outattr = env._df_outattr[sim.sid]
    if outattr:
        # Create a cache entry for every point in time the data is valid for.
        data = sim.get_data(outattr)
        for i in range(sim.time, sim.next_time):
            env._df_cache[i][sim.sid] = data

    # Prune dataflow cache
    min_time = min(s.time for s in env.sims.values())
    for cache_time in env._df_cache.keys():
        if cache_time >= min_time:
            break
        del env._df_cache[cache_time]

    evt = env.simpy_env.event().succeed()
    return evt


def get_progress(sims, until):
    times = [sim.time for sim in sims.values()]
    avg_time = sum(times) / len(times)
    return avg_time * 100 / until
