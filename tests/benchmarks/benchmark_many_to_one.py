import mosaik

from argparser import argparser
from comparison import write_exeuction_graph, compare_execution_graph

args, world_args, run_args = argparser(N=10000, until=10, sim_type='e')
if args.compare:
    world_args['debug'] = True

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

if args.compare:
    compare_execution_graph(world, __file__)

# Write execution_graph to file for comparison
#write_exeuction_graph(world, __file__)
