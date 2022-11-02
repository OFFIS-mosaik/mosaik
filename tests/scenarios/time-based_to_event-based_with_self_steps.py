"""
Scenario 3::

    A(2) → B(1)
"""


def create_scenario(world):
    model_a = world.start('A').A()
    model_b = world.start('B', step_type='event-based', self_steps={0: 2}).A()
    world.connect(model_a, model_b, ('val_out', 'val_in'))


CONFIG = 'generic'

EXECUTION_GRAPH = """
A-0-0 A-0-1
A-0-0 B-0-0
B-0-0 B-0-2
A-0-1 A-0-2
A-0-1 B-0-1
A-0-2 B-0-2
"""

INPUTS = {
    'B-0-0': {'0': {'val_in': {'A-0.0': 0}}},
    'B-0-1': {'0': {'val_in': {'A-0.0': 1}}},
    'B-0-2': {'0': {'val_in': {'A-0.0': 2}}},
}

UNTIL = 3
