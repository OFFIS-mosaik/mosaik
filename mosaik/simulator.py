"""
This module is responsible for performing the simulation of a scenario.

"""
import simpy


def simulation(env, sim_id, sim):
    """SimPy simulation process for a certain simulator *sim* with ID *sim_id*.
    """
    while True:
        start = env.now
        end = sim.step(start)
        print('%s stepped from %s to %s.' % (sim_id, start, end))
        yield env.timeout(end - start)


def run(env, until):
    """Run the simulation for an :class:`~mosaik.scenario.Environment` until
    the simulation time *until* has been reached.

    Return the final simulation time.

    """
    senv = simpy.Environment()
    for sim_id, sim in env.sims.items():
        senv.process(simulation(senv, sim_id, sim))
    senv.run(until=until)
    return senv.now
