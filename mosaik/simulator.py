"""
This module is responsible for performing the simulation of a scenario.

"""
import collections
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
        end = yield step(env, sim)
        logger.debug('%s stepped from %s to %s.' % (sim.sid, start, end))


def step(env, sim):
    outattr = env._df_outattr[sim.sid]
    time, data = sim.step(sim.time, inputs={}, outputs=outattr)
    sim.time = time
    # TODO:
    # - Add "data" to env._df_cache
    # - Get new minimum simulator time
    # - Prune env._df_cache
    evt = env.simpy_env.event()
    evt.succeed(time)
    return evt


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
