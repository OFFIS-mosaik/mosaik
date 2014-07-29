"""
Scenario 1::

   A(1)

"""


def create_scenario(world):
    exsim = world.start('A')
    exsim.A(init_val=0)


execution_graph = """
A-0-0 A-0-1
A-0-1 A-0-2
"""

inputs = {}

until = 3
