"""
Scenario 8::
   A(1) → B()
"""


def create_scenario(world):
    simulator_a = world.start('A')
    simulator_b = world.start('B')
    model_a = simulator_a.A(init_val=0)
    model_b = simulator_b.B(init_val=0)
    #world.connect(model_a, model_b, ('val_out', 'val_in'))


EXECUTION_GRAPH = """
A-0-0 A-0-1
A-0-0 B-0-0
A-0-1 B-0-1
"""

INPUTS = {
    'B-0-0': {'0': {'message_in': {'A-0.0.last_step': [0]}}},
    'B-0-1': {'0': {'message_in': {'A-0.0.last_step': [1]}}},
}

UNTIL = 2
