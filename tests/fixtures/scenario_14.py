"""
Scenario 14::
   A(1) → B()
"""


def create_scenario(world):
    simulator_a = world.start('A')
    simulator_b = world.start('B', self_steps=[2], return_dict=True)
    model_a = simulator_a.TestModel()
    model_b = simulator_b.TestModel()
    world.connect(model_a, model_b, ('last_step', 'message_in'))


EXECUTION_GRAPH = """
A-0-0 A-0-1
A-0-0 B-0-0
B-0-0 B-0-2
A-0-1 A-0-2
A-0-1 B-0-1
A-0-2 B-0-2
"""

INPUTS = {
    'B-0-0': {'0': {'message_in': {'A-0.0.last_step': [0]}}},
    'B-0-1': {'0': {'message_in': {'A-0.0.last_step': [1]}}},
    'B-0-2': {'0': {'message_in': {'A-0.0.last_step': [2]}}},
}

UNTIL = 3
