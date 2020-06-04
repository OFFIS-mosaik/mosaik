"""
Scenario 7::
   A([1, 2, 3])
"""


def create_scenario(world):
    example_simulator = world.start('A', self_steps=[1, 2, 3])
    example_simulator.TestModel()


EXECUTION_GRAPH = """
A-0-0 A-0-1
A-0-1 A-0-2
"""

INPUTS = {}

UNTIL = 3
