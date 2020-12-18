"""
Scenario 19::
   A() → B() → C()
"""


def create_scenario(world):
    model_a = world.start('A', step_type='event-based', self_steps={0: 2},
                          output_timing={0: 0}).A()
    model_b = world.start('B', step_type='event-based').A()
    model_c = world.start('C', step_type='event-based', self_steps={0: 3}).A()
    world.connect(model_a, model_b, ('val_out', 'val_in'))
    world.connect(model_b, model_c, ('val_out', 'val_in'))
    world.set_event(model_a.sid)


EXECUTION_GRAPH = """
A-0-0 A-0-2
A-0-0 B-0-0
B-0-0 C-0-0
C-0-0 C-0-3
"""

INPUTS = {
    'B-0-0': {'b-0': {'val_in': {'A-0.a-0': 0}}},
    'C-0-0': {'c-0': {'val_in': {'B-0.b-0': 0}}},
    'C-0-3': {},
}

UNTIL = 4
