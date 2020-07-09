"""
Scenario 9::
   A(2) → B(1)
"""


def create_scenario(world):
    simulator_a = world.start('A', step_size=2, message_steps=[2])
    simulator_b = world.start('B')
    model_a = simulator_a.TestModel()
    model_b = simulator_b.TestModel()
    world.connect(model_a, model_b, ('last_step_message', 'message_in'))


EXECUTION_GRAPH = """
A-0-0 A-0-2
B-0-0 B-0-1
B-0-1 B-0-2
A-0-2 B-0-2
"""

INPUTS = {
    'B-0-0': {'0': {'message_in': {'A-0.0.last_step_message': []}}},
    'B-0-1': {'0': {'message_in': {'A-0.0.last_step_message': []}}},
    'B-0-2': {'0': {'message_in': {'A-0.0.last_step_message': [2]}}},
}

UNTIL = 3
