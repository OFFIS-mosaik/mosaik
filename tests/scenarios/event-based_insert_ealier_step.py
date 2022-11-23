"""
Scenario 28:
   A → B → C → D

This scenario tests for the right max_advance value if an earlier step is
inserted.
"""


def create_scenario(world):
    model_a = world.start('A', step_type='event-based', self_steps={0: 1, 1: 2}).A()
    model_b = world.start('B', step_type='event-based', self_steps={0: 3}).A()
    model_c = world.start('C', step_type='event-based').A()
    model_d = world.start('D', step_type='event-based').A()
    world.connect(model_a, model_b, ('val_out', 'val_in'))
    world.connect(model_b, model_c, ('val_out', 'val_in'))
    world.connect(model_b, model_d, ('val_out', 'val_in'))
    world.connect(model_c, model_d, ('val_out', 'val_in'))
    world.set_initial_event(model_a.sid, 0)
    world.set_initial_event(model_b.sid, 0)


CONFIG = 'generic'

EXECUTION_GRAPH = """
A-0-0 A-0-1
A-0-0 B-0-0
B-0-0 B-0-3
B-0-0 C-0-0
B-0-0 D-0-0
C-0-0 D-0-0
A-0-1 A-0-2
A-0-1 B-0-1
B-0-1 C-0-1
B-0-1 D-0-1
C-0-1 D-0-1
A-0-2 B-0-2
B-0-2 C-0-2
B-0-2 D-0-2
C-0-2 D-0-2
B-0-3 C-0-3
B-0-3 D-0-3
C-0-3 D-0-3
"""

INPUTS = {
    'B-0-0': {'0': {'val_in': {'A-0.0': 0}}},
    'C-0-0': {'0': {'val_in': {'B-0.0': 0}}},
    'D-0-0': {'0': {'val_in': {'B-0.0': 0, 'C-0.0': 0}}},
    'B-0-1': {'0': {'val_in': {'A-0.0': 1}}},
    'C-0-1': {'0': {'val_in': {'B-0.0': 1}}},
    'D-0-1': {'0': {'val_in': {'B-0.0': 1, 'C-0.0': 1}}},
    'B-0-2': {'0': {'val_in': {'A-0.0': 2}}},
    'C-0-2': {'0': {'val_in': {'B-0.0': 2}}},
    'D-0-2': {'0': {'val_in': {'B-0.0': 2, 'C-0.0': 2}}},
    'C-0-3': {'0': {'val_in': {'B-0.0': 3}}},
    'D-0-3': {'0': {'val_in': {'B-0.0': 3, 'C-0.0': 3}}},
}

UNTIL = 4
