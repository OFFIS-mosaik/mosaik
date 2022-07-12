# benchmark_sparse_time.py
import os
import sys

import mosaik

from argparser import argparser
from comparison import write_exeuction_graph, compare_execution_graph

sys.path.insert(0, os.getcwd())

args, world_args, run_args = argparser(N=10000, until=1000)
if args.plot or args.compare:
    world_args['debug'] = True
run_args['until'] *= args.N
SIM_CONFIG = {
    'ExampleSim': {
        'python': 'simulators.generic_test_simulator:TestSim'
    },
}

# Create World
world = mosaik.World(SIM_CONFIG, **world_args)

# Start simulators und instantiate models:
a = world.start('ExampleSim', step_size=args.N).A()
b = world.start('ExampleSim', step_size=args.N).A()

# Connect entities
world.connect(a, b, ('val_out', 'val_in'))

# Run simulation
world.run(**run_args)

# Write execution_graph to file for comparison
#write_exeuction_graph(world, __file__)

if args.compare:
    compare_execution_graph(world, __file__)
