"""
Scenario 17::
   A() → B() → C() → A()
"""


def create_scenario(world):
    model_a = world.start('A', step_type='event-based', output_timing={0: 2}).A()
    model_b = world.start('B', step_type='event-based', output_timing={2: 3}).A()
    model_c = world.start('C', step_type='event-based', output_timing={3: 5}).A()
    world.connect(model_a, model_b, ('val_out', 'val_in'))
    world.connect(model_b, model_c, ('val_out', 'val_in'))
    world.connect(model_c, model_a, ('val_out', 'val_in'), weak=True)
    world.set_event(model_a.sid)


EXECUTION_GRAPH = """
A-0-0 B-0-2
B-0-2 C-0-3
C-0-3 A-0-5
"""

INPUTS = {
    'B-0-2': {'b-0': {'val_in': {'A-0.a-0': 0}}},
    'C-0-3': {'c-0': {'val_in': {'B-0.b-0': 2}}},
    'A-0-5': {'a-0': {'val_in': {'C-0.c-0': 3}}},
}

UNTIL = 6
