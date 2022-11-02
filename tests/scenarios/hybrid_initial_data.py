"""
Scenario 21::
   A() ⇄ B()

This scenario tests if the data provided in initial_data is sent correcntly from a hybrid simulator to a
time-based simulator
"""


def create_scenario(world):
    model_a = world.start('A', step_type='time-based').A()
    model_b = world.start('B', step_type='hybrid', self_steps={0: 1}).A()
    world.connect(model_a, model_b, ('val_out', 'val_in'))
    world.connect(model_b, model_a, ('val_out', 'val_in'), time_shifted=True, initial_data={'val_out': -1})


CONFIG = 'generic'

EXECUTION_GRAPH = """
A-0-0 A-0-1
A-0-0 B-0-0
B-0-0 A-0-1
B-0-0 B-0-1
A-0-1 B-0-1
"""

INPUTS = {
    'A-0-0': {'0': {'val_in': {'B-0.0': -1}}},
    'A-0-1': {'0': {'val_in': {'B-0.0': 0}}},
    'B-0-0': {'0': {'val_in': {'A-0.0': 0}}},
    'B-0-1': {'0': {'val_in': {'A-0.0': 1}}},
}

UNTIL = 2
