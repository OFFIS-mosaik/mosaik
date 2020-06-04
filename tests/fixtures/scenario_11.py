"""
Scenario 8::
   A([])
"""


def create_scenario(world):
    example_simulator = world.start('A', self_steps=[], continuous=False)
    example_model = example_simulator.TestModel()
    world.set_event(example_model.sid)


EXECUTION_GRAPH = """
"""

INPUTS = {
    'A-0-0': {},
}


UNTIL = 2
