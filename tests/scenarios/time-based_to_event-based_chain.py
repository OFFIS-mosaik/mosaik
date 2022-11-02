"""
Scenario 23:
   A → B → C

This scenario tests for a deadlock caused by lazy_stepping if event-based
successor is not triggered.
"""


def create_scenario(world):
    model_a = world.start('A', step_type='time-based', step_size=3,
                          output_timing={0: 0}).A()
    model_b = world.start('B', step_type='event-based', self_steps={0: 2},
                          output_timing={}).A()
    model_c = world.start('C', step_type='event-based').A()
    world.connect(model_a, model_b, ('val_out', 'val_in'))
    world.connect(model_a, model_c, ('val_out', 'val_in'))
    world.connect(model_b, model_c, ('val_out', 'val_in'))
    world.set_initial_event(model_b.sid, 1)
    world.set_initial_event(model_c.sid, 1)


CONFIG = 'generic'

EXECUTION_GRAPH = """
A-0-0 A-0-3
A-0-0 C-0-0
A-0-0 B-0-0
A-0-0 C-0-1
A-0-0 B-0-1
A-0-0 B-0-2
B-0-0 B-0-2
A-0-3 A-0-6
"""

INPUTS = {
    'B-0-0': {'0': {'val_in': {'A-0.0': 0}}},
    'C-0-0': {'0': {'val_in': {'A-0.0': 0}}},
    'B-0-1': {'0': {'val_in': {'A-0.0': 0}}},
    'C-0-1': {'0': {'val_in': {'A-0.0': 0}}},
    'B-0-2': {'0': {'val_in': {'A-0.0': 0}}},
}

UNTIL = 7
