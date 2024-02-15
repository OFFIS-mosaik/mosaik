"""
Scenario 24:
   A ⇄ B ⇄ C

This scenario tests for chained cyclic dependencies.
"""
from mosaik import World


def create_scenario(world: World):
    with world.group():
        with world.group():
            model_a = world.start('A', sim_id="A", step_type='event-based', self_steps={0: 4},
                                output_timing={0: 0}).A()
            model_b = world.start('B', sim_id="B", step_type='event-based', self_steps={0: 2},
                                output_timing={2: 2}).A()
        model_c = world.start('C', sim_id="C", step_type='event-based').A()
    world.connect(model_a, model_b, ('val_out', 'val_in'))
    world.connect(model_b, model_a, ('val_out', 'val_in'), weak=True)
    world.connect(model_b, model_c, ('val_out', 'val_in'))
    world.connect(model_c, model_b, ('val_out', 'val_in'), weak=True)
    world.set_initial_event(model_a.sid, 0)


CONFIG = 'generic'
WEAK = True

EXECUTION_GRAPH = """
A~0:0:0 A~4:0:0
A~0:0:0 B~0:0:0
B~0:0:0 B~2:0:0
B~2:0:0 A~2:0:1
B~2:0:0 C~2:0
C~2:0   B~2:1:0
"""

INPUTS = {
    'B~0:0:0': {'0': {'val_in': {'A.0': 0}}},
    'A~2:0:1': {'0': {'val_in': {'B.0': 2}}},
    'C~2:0': {'0': {'val_in': {'B.0': 2}}},
    'B~2:1:0': {'0': {'val_in': {'C.0': 2}}},
}

UNTIL = 7
