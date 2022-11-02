"""
Scenario 16::
   A() → B()
"""


def create_scenario(world):
    model_a = world.start('A', step_type='event-based', output_timing={0: 2}).A()
    model_b = world.start('B', step_type='time-based').A()
    world.connect(model_a, model_b, ('val_out', 'val_in'))
    world.set_initial_event(model_a.sid)


CONFIG = 'generic'

EXECUTION_GRAPH = """
A-0-0 B-0-2
B-0-0 B-0-1
B-0-1 B-0-2
"""

INPUTS = {
    'B-0-2': {'0': {'val_in': {'A-0.0': 0}}},
}

UNTIL = 3
