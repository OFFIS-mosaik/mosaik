"""
Scenario 24:
   A ⇄ B ⇄ C

This scenario tests for chained cyclic dependencies.
"""


def create_scenario(world):
    model_a = world.start('A', step_type='event-based', self_steps={0: 4},
                          output_timing={0: 0}).A()
    model_b = world.start('B', step_type='event-based', self_steps={0: 2},
                          output_timing={2: 3}).A()
    model_c = world.start('C', step_type='event-based').A()
    world.connect(model_a, model_b, ('val_out', 'val_in'))
    world.connect(model_b, model_a, ('val_out', 'val_in'), weak=True)
    world.connect(model_b, model_c, ('val_out', 'val_in'))
    world.connect(model_c, model_b, ('val_out', 'val_in'), weak=True)
    world.set_event(model_a.sid, 0)


CONFIG = 'generic'

EXECUTION_GRAPH = """
A-0-0 A-0-4
A-0-0 B-0-0
B-0-0 B-0-2
B-0-2 A-0-3
B-0-2 C-0-3
C-0-3 B-0-3
"""

INPUTS = {
    'B-0-0': {'b-0': {'val_in': {'A-0.a-0': 0}}},
    'A-0-3': {'a-0': {'val_in': {'B-0.b-0': 2}}},
    'C-0-3': {'c-0': {'val_in': {'B-0.b-0': 2}}},
    'B-0-3': {'b-0': {'val_in': {'C-0.c-0': 3}}},
}

UNTIL = 7
