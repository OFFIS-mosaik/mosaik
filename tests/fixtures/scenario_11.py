"""
Scenario 11::
   A() → B()
"""


def create_scenario(world):
    model_a = world.start('A', step_type='discrete-event',
                          self_steps={0: 1, 1: 3}).A()
    model_b = world.start('B', step_size=2).A()
    world.set_event(model_a.sid)
    world.connect(model_a, model_b, ('val_out', 'val_in'))


EXECUTION_GRAPH = """
A-0-0 A-0-1
A-0-0 B-0-0
B-0-0 B-0-2
A-0-1 B-0-2
"""

INPUTS = {
    'B-0-0': {'b-0': {'val_in': {'A-0.a-0': 0}}},
    'B-0-2': {},
}

UNTIL = 3
