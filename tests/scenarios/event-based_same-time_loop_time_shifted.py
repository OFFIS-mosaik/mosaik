"""
This scenario has two event-based simulators in a time-shifted loop. The second
simulator's output should be delayed due to the time shift, so that the simulators
do not enter a same-time loop.

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
B-0-0 A-0-1
A-0-1 B-0-1
"""

INPUTS = {
    'B-0-0': {'0': {'val_in': {'A-0.0': 0}}},
    'A-0-1': {'0': {'val_in': {'B-0.0': 0}}},
    'B-0-1': {'0': {'val_in': {'A-0.0': 1}}},
}

UNTIL = 2
