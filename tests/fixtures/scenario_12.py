"""
Scenario 12::
   A(2) → C(): message at 2 (supposed to be scheduled earlier than from B)
   B(1) → C(): message at 1
"""


def create_scenario(world):
    simulator_a = world.start('A', step_size=2, message_steps=[2])
    simulator_b = world.start('B', step_size=1, message_steps=[1])
    simulator_c = world.start('C', self_steps=[], continuous=False)
    model_a = simulator_a.TestModel()
    model_b = simulator_b.TestModel()
    model_c = simulator_c.TestModel()
    print(model_a.sim.meta)
    world.connect(model_a, model_c, ('last_step_message', 'message_in'))
    world.connect(model_b, model_c, ('last_step_message', 'message_in'))
    world.connect(model_a, model_b, ('last_step', 'inputs'))


EXECUTION_GRAPH = """
A-0-0 A-0-2
A-0-0 B-0-0
A-0-0 B-0-1
B-0-0 B-0-1
B-0-1 B-0-2
B-0-1 C-0-1
A-0-2 B-0-2
A-0-2 C-0-2
"""

INPUTS = {
    'B-0-0': {'0': {'inputs': {'A-0.0': 0}}},
    'B-0-1': {'0': {'inputs': {'A-0.0': 0}}},
    'B-0-2': {'0': {'inputs': {'A-0.0': 2}}},
    'C-0-1': {'0': {'message_in': {'B-0.0.last_step_message': [1]}}},
    'C-0-2': {'0': {'message_in': {'A-0.0.last_step_message': [2]}}},
}

UNTIL = 3
LAZY_STEPPING = False
