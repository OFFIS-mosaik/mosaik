"""
In this scenario we have two simulators, the first simulator has two outputs, 
one is connected to the trigger input and one is connected to the 
non-trigger input of the other simulator. Then an output of the first simulator 
triggers on the second attribute of the other simulator, although the input is
non-trigger.
"""


def create_scenario(world):
    sim_0 = world.start('A', step_size=1)
    ent_0 = sim_0.A()

    sim_1 = world.start('B', step_type='hybrid', trigger=['trigger_in'])
    ent_1 = sim_1.A()

    world.connect(ent_0, ent_1, ('never_out', 'trigger_in'), ('val_out', 'val_in'))


CONFIG = 'generic'

EXECUTION_GRAPH = """
A-0-0 B-0-0
A-0-0 A-0-1
"""

INPUTS = {
    'B-0-0': {'0': {'trigger_in': {'A-0.0': None}, 'val_in': {'A-0.0': 0}}},
}

INPUTS_WITH_CACHE = {
    'B-0-0': {'0': {'val_in': {'A-0.0': 0}}},
}

UNTIL = 2
