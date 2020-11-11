"""
Scenario 16::
   A() → B()
"""


def create_scenario(world):
    model_a = world.start('A', step_type='discrete-event', output_timing={0: 2}).A()
    model_b = world.start('B', step_type='discrete-time').A()
    world.connect(model_a, model_b, ('val_out', 'val_in'))
    world.set_event(model_a.sid)


EXECUTION_GRAPH = """
A-0-0 B-0-0
A-0-0 B-0-1
A-0-0 B-0-2
B-0-0 B-0-1
B-0-1 B-0-2
"""

INPUTS = {
    'B-0-2': {'b-0': {'val_in': {'A-0.a-0': 0}}},
}

UNTIL = 3
