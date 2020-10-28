"""
Scenario 13::
   A() → B()
"""


def create_scenario(world):
    model_a = world.start('A', step_type='discrete-event',
                          self_steps={0: 1, 1: 3},
                          output_timing={0: 0, 1: None}).A()
    model_b = world.start('B', step_type='discrete-event').A()
    world.set_event(model_a.sid)
    world.connect(model_a, model_b, ('val_out', 'val_in'))


EXECUTION_GRAPH = """
A-0-0 A-0-1
A-0-0 B-0-0
"""

INPUTS = {
    'B-0-0': {'b-0': {'val_in': {'A-0.a-0': 0}}},
}

UNTIL = 3
