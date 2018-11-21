"""
Scenario 1::
   A(1)
"""


def create_scenario(world):
    example_simulator = world.start('A')
    example_simulator.A(init_val=0)


EXECUTION_GRAPH = """
A-0-0 A-0-1
A-0-1 A-0-2
"""

INPUTS = {}

UNTIL = 3
