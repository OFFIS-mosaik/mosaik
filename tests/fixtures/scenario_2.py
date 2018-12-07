"""
Scenario 2::

    A(1) → B(1)
"""


def create_scenario(world):
    simulator_a = world.start('A')
    simulator_b = world.start('B')
    model_a = simulator_a.A(init_val=0)
    model_b = simulator_b.B(init_val=0)
    world.connect(model_a, model_b, ('val_out', 'val_in'))


EXECUTION_GRAPH = """
A-0-0 A-0-1
A-0-0 B-0-0
A-0-1 B-0-1
B-0-0 B-0-1
"""

INPUTS = {
    'B-0-0': {'0.0': {'val_in': {'A-0.0.0': 1}}},
    'B-0-1': {'0.0': {'val_in': {'A-0.0.0': 2}}},
}

UNTIL = 2
