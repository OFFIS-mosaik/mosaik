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
    env.simpy_env = env
    for sim in env.sims.values():
        senv.process(simulation(env, sim))
    senv.run(until=until)
    return senv.now


def simulation(env, sim):
    """SimPy simulation process for a certain simulator *sim*.
    """
    while True:
        start = env.simpy_env.now
        end = yield step(env, sim, start)
        logger.debug('%s stepped from %s to %s.' % (sim.id, start, end))


def step(env, sim, start):
    gen = sim.step(start)
    try:
        get_data_params = next(gen)
        while True:
            data = get_data(env, sim, **get_data_params)
            get_data_params = gen.send(data)
    except StopIteration as e:
        end = e.args[0]
        return env.simpy_env.timeout(end - start, value=end)


def get_data(env, sim, start, end):
    input_sims = env._get_input_sims(sim_id)
    env._data_cache(
    check_env_cache()
    get_data_from_sim()
    pass
