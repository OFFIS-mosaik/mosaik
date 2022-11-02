"""
Scenario 26:
   A ⇄ B ⇄ C

This scenario tests for chained cyclic dependencies.
"""


def create_scenario(world):
    model_a = world.start('A', step_type='event-based', self_steps={0: 4},
                          output_timing={0: 0}).A()
    model_b = world.start('B', step_type='event-based', self_steps={0: 2},
                          output_timing={0: 0}).A()
    model_c = world.start('C', step_type='event-based').A()
    world.connect(model_a, model_b, ('val_out', 'val_in'))
    world.connect(model_b, model_a, ('val_out', 'val_in'), weak=True)
    world.connect(model_b, model_c, ('val_out', 'val_in'))
    world.connect(model_c, model_b, ('val_out', 'val_in'), weak=True)
    world.set_initial_event(model_b.sid, 0)


CONFIG = 'generic_remote'

EXECUTION_GRAPH = """
B-0-0 B-0-2
B-0-0 A-0-0
A-0-0 A-0-4
A-0-0 B-0-0~1
B-0-0~1 B-0-2
B-0-0~1 C-0-0
C-0-0 B-0-0~2
B-0-0~2 B-0-2
"""

INPUTS = {
    'A-0-0': {'0': {'val_in': {'B-0.0': 0}}},
    'C-0-0': {'0': {'val_in': {'B-0.0': 0}}},
    'B-0-0~1': {'0': {'val_in': {'A-0.0': 0}}},
    'B-0-0~2': {'0': {'val_in': {'C-0.0': 0}}},
}

UNTIL = 7
