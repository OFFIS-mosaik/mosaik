"""
This scenario consists of two event-based simulators in a loop. If they are connected as time_shifted
and the simulator B return the current time as timestamp for it's output data, they enter a same time loop,
which should not be the case.

  A ⇄ B

where the connection from B to A is time_shifted.
"""


def create_scenario(world):
    model_a = world.start('A', step_type='event-based').A()
    model_b = world.start('B', step_type='event-based', output_timing={0: [0, 0, 1]}).A()
    world.set_initial_event(model_a.sid)
    world.connect(model_a, model_b, ('val_out', 'val_in'))
    world.connect(model_b, model_a, ('val_out', 'val_in'), initial_data={'val_out': 0}, time_shifted=True)

CONFIG = 'generic'

EXECUTION_GRAPH = """
A-0-0 B-0-0
"""

INPUTS = {
    'B-0-0': {'0': {'val_in': {'A-0.0': 0}}},
}

UNTIL = 1
