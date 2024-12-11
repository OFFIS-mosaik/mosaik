# benchmark_one_to_many.py
import os
import sys

from argparser import argparser
from comparison import compare_execution_graph

import mosaik

sys.path.insert(0, os.getcwd())

args, world_args, run_args = argparser(N=10000, until=10)
if args.plot or args.compare:
    world_args["debug"] = True

SIM_CONFIG = {
    "TestSim": {
        "python": "tests.simulators.generic_test_simulator:TestSim",
    },
}

world = mosaik.World(SIM_CONFIG, **world_args)

if args.sim_type == "time":
    step_type = "time-based"
    stepping = {"step_size": 1}
else:
    step_type = "event-based"
    stepping = {"self_steps": {i: i + 1 for i in range(args.until)}}

a = world.start("TestSim", step_type=step_type, **stepping).A.create(1)
b = world.start("TestSim", step_type=step_type, **stepping).A.create(args.N)

for ib in b:
    world.connect(a[0], ib, ("val_out", "val_in"))

world.run(**run_args)

# Write execution_graph to file for comparison
# write_exeuction_graph(world, __file__)

if args.compare:
    compare_execution_graph(world, __file__)
