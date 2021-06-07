import os
import sys

import mosaik

from argparser import argparser

sys.path.insert(0, os.getcwd())
from tests.plotting.execution_graph_tools import plot_execution_graph


args, world_args, run_args = argparser(until=10)
if args.plot:
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
    plot_execution_graph(world)
