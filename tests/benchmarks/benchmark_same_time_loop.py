#benchmark_same_time_loop.py
import os
import sys

import mosaik

from argparser import argparser
from comparison import write_exeuction_graph, compare_execution_graph

sys.path.insert(0, os.getcwd())

args, world_args, run_args = argparser(until=10, sim_type='event')
if args.plot or args.compare:
    world_args['debug'] = True

SIM_CONFIG = {
    0: {'TestSim': {'python': 'simulators.generic_test_simulator:TestSim'}},
    1: {'TestSim': {'cmd': '%(python)s tests/simulators/generic_test_simulator.py %(addr)s'}}
}

world = mosaik.World(SIM_CONFIG[args.remote], **world_args)

if args.sim_type == 'time':
    step_type = 'time-based'
    connection_args = {
        'time_shifted': True,
        'initial_data': {'val_out': 0}
    }
else:
    step_type = 'event-based'
    connection_args = {
        'weak': True
    }

output_timing = {0: [0, 0, 0, 1],
                 1: [1, 1, 2],
                 2: 5,
                 5: [5, 5, 5, 8],
                 8: [10],
                 }

a = world.start('TestSim', step_type=step_type).A()
b = world.start('TestSim', step_type=step_type, output_timing=output_timing).A()
world.set_initial_event(a.sid)

world.connect(a, b, ('val_out', 'val_in'))
world.connect(b, a, ('val_out', 'val_in'), **connection_args)

world.run(**run_args)

if args.plot:
    from plotting.execution_graph_tools import plot_execution_graph_st
    plot_execution_graph_st(world)

if args.compare:
    compare_execution_graph(world, __file__)

# Write execution_graph to file for comparison
#write_exeuction_graph(world, __file__)
