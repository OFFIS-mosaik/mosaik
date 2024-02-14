"""
Scenario 25:
   A → B ⇄ C

This scenario tests for a specific deadlock in cyclic dependencies.
"""


from mosaik.scenario import World


def create_scenario(world: World):
    model_a = world.start('A', step_type='event-based', self_steps={0: 1},
                          output_timing={}).A()
    with world.group():
        model_b = world.start('B', step_type='event-based', self_steps={},
                            output_timing={}).A()
        model_c = world.start('C', step_type='event-based').A()
    world.connect(model_a, model_b, ('val_out', 'val_in'))
    world.connect(model_b, model_c, ('val_out', 'val_in'))
    world.connect(model_c, model_b, ('val_out', 'val_in'), weak=True)
    world.set_initial_event(model_a.sid, 0)
    world.set_initial_event(model_b.sid, 0)


CONFIG = 'generic'
WEAK = True

EXECUTION_GRAPH = """
A-0~0 A-0~1
"""

INPUTS = {
    'B-0~0': {},
}

UNTIL = 7
