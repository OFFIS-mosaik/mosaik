"""
Scenario 31::
C
  ↘
    B → D
  ↗
A
"""


def create_scenario(world):
    model_a = world.start('A', step_type='time-based', step_size=1).A()
    model_b = world.start('B', step_type='event-based', trigger=['val_in']).A()
    model_c = world.start('C', step_type='time-based', step_size=1).A()
    model_d = world.start('D', step_type='time-based', step_size=1).A()
    world.connect(model_c, model_b, ('val_out', 'val_in'))
    world.connect(model_a, model_b, ('val_out', 'val_in'))
    world.connect(model_b, model_d, ('val_out', 'val_in'))

CONFIG = 'generic'

EXECUTION_GRAPH = """
A-0-0 B-0-0
C-0-0 B-0-0
B-0-0 D-0-0
A-0-0 A-0-1
C-0-0 C-0-1
D-0-0 D-0-1
A-0-1 B-0-1
C-0-1 B-0-1
B-0-1 D-0-1
"""

INPUTS = {
    'B-0-0': {'0': {'val_in': {'A-0.0': 0, 'C-0.0': 0}}},
    'D-0-0': {'0': {'val_in': {'B-0.0': 0}}},
    'B-0-1': {'0': {'val_in': {'A-0.0': 1, 'C-0.0': 1}}},
    'D-0-1': {'0': {'val_in': {'B-0.0': 1}}},
}

UNTIL = 2
