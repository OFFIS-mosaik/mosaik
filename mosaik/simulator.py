import simpy


def simulation(env, sim_id, sim):
    while True:
        start = env.now
        end = sim.step(start)
        print('%s stepped from %s to %s.' % (sim_id, start, end))
        yield env.timeout(end - start)


def run(env, until):
    senv = simpy.Environment()
    for sim_id, sim in env.sims.items():
        senv.process(simulation(senv, sim_id, sim))
    senv.run(until=until)
    return senv.now
