"""
Scenario 20::
   A() → B() → C()
"""


def create_scenario(world):
    model_a = world.start('A', step_type='event-based', self_steps={0: 2},
                          output_timing={}).A()
    model_b = world.start('B', step_type='event-based').A()
    model_c = world.start('C', step_type='hybrid', self_steps={0: 3}).A()
    world.connect(model_a, model_b, ('val_out', 'val_in'))
    world.connect(model_b, model_c, ('val_out', 'val_in'))
    world.set_initial_event(model_a.sid)


CONFIG = 'generic'

EXECUTION_GRAPH = """
A-0-0 A-0-2
C-0-0 C-0-3
"""

INPUTS = {
    'C-0-0': {},
    'C-0-3': {},
}

UNTIL = 4
