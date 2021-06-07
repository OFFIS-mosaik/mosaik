import mosaik

from argparser import argparser

args, world_args, run_args = argparser(N=10000, until=10, sim_type='e')

SIM_CONFIG = {
    'TestSim': {
        'python': 'tests.simulators.generic_test_simulator:TestSim',
    },
}

world = mosaik.World(SIM_CONFIG, **world_args)

if args.sim_type == 'time':
    step_type = 'time-based'
    stepping = {'step_size': 1}
else:
    step_type = 'event-based'
    stepping = {'self_steps': {i: i+1 for i in range(args.until)}}

a = world.start('TestSim', step_type=step_type, **stepping).A.create(args.N)
if args.sim_type == 'event':
    world.set_initial_event(a[0].sid)
b = world.start('TestSim', step_type=step_type, **stepping).A.create(1)

mosaik.util.connect_many_to_one(world, a, b[0], ('val_out', 'val_in'))

world.run(**run_args)
