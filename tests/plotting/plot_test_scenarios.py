"""
Plots the executions graphs of the test scenarios in tests/fixtures/.

"""

import glob
import importlib
import networkx as nx
import os
import sys

from mosaik import scenario

from execution_graph_tools import plot_execution_graph_st as plot_execution_graph
sys.path.insert(0, os.getcwd())
from tests.test_mosaik import sim_config


def plot_test_case(test_case):
    test_module = importlib.import_module('tests.fixtures.%s' % test_case)
    world = scenario.World(sim_config[test_module.CONFIG], debug=True)
    try:
        test_module.create_scenario(world)
        if not hasattr(test_module, 'RT_FACTOR'):
            world.run(until=test_module.UNTIL)
        else:
            world.run(until=test_module.UNTIL, rt_factor=test_module.RT_FACTOR)

        plot_execution_graph(world, test_case)
    finally:
        world.shutdown()


sys.path.insert(0, os.getcwd())
test_cases = [os.path.basename(file).strip('.py')
              for file in glob.glob('tests/fixtures/scenario_*.py')]

for test_case in test_cases:
    plot_test_case(test_case)
