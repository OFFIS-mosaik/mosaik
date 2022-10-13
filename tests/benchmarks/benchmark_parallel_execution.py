#benchmark_parallel_execution.py
import os
import sys

import mosaik

from argparser import argparser
from comparison import write_exeuction_graph, compare_execution_graph

sys.path.insert(0, os.getcwd())

args, world_args, run_args = argparser(until=10)
if args.plot or args.compare:
    world_args['debug'] = True

SIM_CONFIG = {
    0: {'TestSim': {'python': 'tests.simulators.generic_test_simulator:TestSim'}},
    1: {'TestSim': {'cmd': '%(python)s tests/simulators/generic_test_simulator.py %(addr)s'}}
}

world = mosaik.World(SIM_CONFIG[args.remote], **world_args)

a = world.start('TestSim', step_size=1, wallclock_duration=.05).A()
b = world.start('TestSim', step_size=1, wallclock_duration=.05).A()

world.connect(a, b, ('val_out', 'val_in'))

world.run(**run_args)

if args.plot:
	from plotting.execution_graph_tools import plot_execution_graph
	plot_execution_graph(world)

# Write execution_graph to file for comparison
# write_exeuction_graph(world, __file__)

if args.compare:
    compare_execution_graph(world, __file__)
