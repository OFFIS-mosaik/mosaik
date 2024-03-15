"""
Scenario 29:
   A → B

This scenario tests that self-stepping simulators run until they're done even
if their successors have already finished. This is a change in the intended
behaviour.
"""


def create_scenario(world):
    model_a = world.start('A', step_size=1).A()
    model_b = world.start('B', step_type='hybrid').A()
    world.connect(model_a, model_b, ('val_out', 'val_in'))


CONFIG = 'generic'

EXECUTION_GRAPH = """
A-0~0 A-0~1
A-0~0 B-0~0
A-0~1 A-0~2
A-0~2 A-0~3
"""

INPUTS = {
    'B-0~0': {'0': {'val_in': {'A-0.0': 0}}},
}

UNTIL = 4
