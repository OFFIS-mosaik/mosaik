"""
Scenario 12::
   A() → B(2)
"""


def create_scenario(world):
    model_a = world.start('A', step_type='hybrid',
                          self_steps={0: 1, 1: 3}).A()
    model_b = world.start('B', step_size=2).A()
    world.set_initial_event(model_a.sid)
    world.connect(model_a, model_b, ('val_out', 'val_in'))


CONFIG = 'generic'

EXECUTION_GRAPH = """
A-0-0 A-0-1
A-0-0 B-0-0
B-0-0 B-0-2
A-0-1 B-0-2
"""

INPUTS = {
    'B-0-0': {'0': {'val_in': {'A-0.0': 0}}},
    'B-0-2': {'0': {'val_in': {'A-0.0': 1}}},
}

UNTIL = 3
