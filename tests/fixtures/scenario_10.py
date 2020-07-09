"""
Scenario 10::
   A([0]) → B([2])
"""


def create_scenario(world):
    simulator_a = world.start('A', self_steps=[], continuous=False)
    simulator_b = world.start('B', self_steps=[2], message_steps=[2],
                              continuous=False)
    model_a = simulator_a.TestModel()
    model_b = simulator_b.TestModel()
    world.connect(model_a, model_b, ('last_step_message', 'message_in'))
    world.connect(model_b, model_a, ('last_step_message', 'message_in'), weak=True)
    world.set_event(model_b.sid)


EXECUTION_GRAPH = """
B-0-0 B-0-2
B-0-2 A-0-2
"""

INPUTS = {
    'B-0-0': {'0': {'message_in': {'A-0.0.last_step_message': []}}},
    'B-0-2': {'0': {'message_in': {'A-0.0.last_step_message': []}}},
    'A-0-2': {'0': {'message_in': {'B-0.0.last_step_message': [2]}}},
}

UNTIL = 4
