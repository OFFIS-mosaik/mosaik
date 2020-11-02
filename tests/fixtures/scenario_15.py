"""
Scenario 15::
   A() → B()
"""


def create_scenario(world):
    model_a = world.start('A', step_type='discrete-event', output_timing={0: 2}).A()
    model_b = world.start('B', step_type='discrete-event').A()
    world.connect(model_a, model_b, ('val_out', 'val_in'))
    world.connect(model_b, model_a, ('val_out', 'val_in'), weak=True)
    world.set_event(model_a.sid)


EXECUTION_GRAPH = """
A-0-0 B-0-2
B-0-2 A-0-2
"""

INPUTS = {
    'B-0-2': {'b-0': {'val_in': {'A-0.a-0': 0}}},
    'A-0-2': {'a-0': {'val_in': {'B-0.b-0': 2}}},
}

UNTIL = 3
