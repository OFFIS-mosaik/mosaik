"""
Scenario 10::
   A() → B() → C()
    \_________↗
"""


def create_scenario(world):
    model_a = world.start('A', step_type='event-based', self_steps={0: 3},
                          output_timing={0: 0}).A()
    model_b = world.start('B', step_type='hybrid').A()
    model_c = world.start('C', step_type='event-based', self_steps={0: 3}).A()
    world.connect(model_a, model_b, ('val_out', 'val_in'))
    world.connect(model_b, model_c, ('val_out', 'val_in'))
    world.set_initial_event(model_a.sid)


CONFIG = 'generic'

EXECUTION_GRAPH = """
A-0-0 A-0-3
A-0-0 B-0-0
B-0-0 C-0-0
B-0-0 C-0-3
C-0-0 C-0-3
"""

INPUTS = {
    'B-0-0': {'0': {'val_in': {'A-0.0': 0}}},
    'C-0-0': {'0': {'val_in': {'B-0.0': 0}}},
    'C-0-3': {'0': {'val_in': {'B-0.0': 0}}},
}

UNTIL = 4
