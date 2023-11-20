"""
Scenario 18::
   A() → B()
"""

from mosaik.scenario import World

#SKIP = [True, False]

def create_scenario(world: World):
    model_a = world.start('A', step_type='event-based', events={0.05: 1, 0.1: 2}).A()
    model_b = world.start('B', step_type='event-based').A()
    world.connect(model_a, model_b, ('val_out', 'val_in'))


CONFIG = 'generic_remote'

EXECUTION_GRAPH = """
A-0-1 B-0-1
"""

INPUTS = {
    'B-0-1': {'0': {'val_in': {'A-0.0': 1}}},
}

UNTIL = 2
RT_FACTOR = .1
