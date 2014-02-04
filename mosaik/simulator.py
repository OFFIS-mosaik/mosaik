"""
This module is responsible for performing the simulation of a scenario.

"""
import logging

import simpy


logger = logging.getLogger(__name__)


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
    # dfg = env.df_graph
    # deps = dfg.predecessors(sim['sid'])
    while sim.time < until:
        # data = {}
        # for dep in deps:
        #     data[dep] = yield get_data(dep, now)
        start = sim.time
        yield step(env, sim)
        logger.debug('%s stepped from %s to %s.' % (sim.sid, start, sim.time))
        logger.info('Progress: %5.3f%%' % get_progress(env.sims, until))


def step(env, sim):
    outattr = env._df_outattr[sim.sid]
    time = sim.step(sim.time, inputs={})
    if outattr:
        data = sim.get_data(outattr)
        env._df_cache[sim.time][sim.sid] = data
    sim.time = time

    # Prune dataflow cache
    min_time = min(s.time for s in env.sims.values())
    for cache_time in env._df_cache.keys():
        if cache_time >= min_time:
            break
        del env._df_cache[cache_time]

    evt = env.simpy_env.event()
    evt.succeed(time)
    return evt


def get_progress(sims, until):
    times = [sim.time for sim in sims.values()]
    avg_time = sum(times) / len(times)
    return avg_time * 100 / until


# def get_data(sim, data, time):
#     """Return an event that waits until *sim* provides the required *data* for
#     a certain *time*.
#
#     The event succeeds when the data is avaialbe. The events value will be the
#     data.
#
#     """
#     input_sims = env._get_input_sims(sim_id)
#     env._data_cache(
#     check_env_cache()
#     get_data_from_sim()
#     pass
