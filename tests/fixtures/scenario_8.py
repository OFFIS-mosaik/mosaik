"""
Scenario 9::
   A(1) → B()
"""


def create_scenario(world):
    model_a = world.start('A').A()
    model_b = world.start('B', step_type='event-based').A()
    world.connect(model_a, model_b, ('val_out', 'val_in'))


CONFIG = 'generic'

EXECUTION_GRAPH = """
A-0-0 A-0-1
A-0-0 B-0-0
A-0-1 B-0-1
"""

INPUTS = {
    'B-0-0': {'0': {'val_in': {'A-0.0': 0}}},
    'B-0-1': {'0': {'val_in': {'A-0.0': 1}}},
}

UNTIL = 2
