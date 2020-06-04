"""
Scenario 10::
   A([0]) → B([2])
"""


def create_scenario(world):
    simulator_a = world.start('A', self_steps=[])
    simulator_b = world.start('B', self_steps=[2], message_steps=[2])
    model_a = simulator_a.TestModel()
    model_b = simulator_b.TestModel()
    world.connect(model_a, model_b, ('last_step_message', 'message_in'))
    world.connect(model_b, model_a, ('last_step_message', 'message_in'), weak=True)


EXECUTION_GRAPH = """
B-0-0 B-0-2
B-0-2 A-0-2
"""

INPUTS = {
    'A-0-0': {},
    'A-0-2': {'0': {'message_in': {'B-0.0.last_step_message': [2]}}},
}

UNTIL = 4
