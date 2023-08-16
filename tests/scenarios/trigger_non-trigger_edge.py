"""
In this scenario, we add two edges between the same simulators, one trigger,
one non-trigger. The second edge's non-triggering behaviour should not
overwrite the first edges triggering behaviour.
"""

def create_scenario(world):
    sim_0 = world.start('A', step_size=1)
    ent_0 = sim_0.A()

    sim_1 = world.start('B', step_type='hybrid', trigger=['trigger_in'])
    ent_1 = sim_1.A()


    world.connect(ent_0, ent_1, ('val_out', 'trigger_in'))
    world.connect(ent_0, ent_1, ('val_out', 'val_in'))

CONFIG = 'generic'

EXECUTION_GRAPH = """
A-0-0 B-0-0
A-0-0 A-0-1
A-0-1 B-0-1
"""

INPUTS = {
    'B-0-0': {'0': {'trigger_in': {'A-0.0': 0}, 'val_in': {'A-0.0': 0}}},
    'B-0-1': {'0': {'trigger_in': {'A-0.0': 1}, 'val_in': {'A-0.0': 1}}},
}

UNTIL = 2