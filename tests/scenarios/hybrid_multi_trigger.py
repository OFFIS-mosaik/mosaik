"""
Tests whether multiple connect calls lead to the unexpected behavior that a trigger 
connection between two simulators is forgotten / overwritten. This happens as mosaik 
stores the information about triggers per simulator and not per attribute.
"""


def create_scenario(world):
    sim_0 = world.start("A", step_size=1)
    ent_0 = sim_0.A()
    sim_1 = world.start("A", step_type="hybrid")
    ent_1 = sim_1.A()
    world.connect(ent_0, ent_1, ("val_out", "trigger_in"))

    # When you uncomment the following line, the test should fail (in the old,
    # wrong mosaik version)
    # world.connect(ent_0, ent_1, ('val_out', 'val_in'))


CONFIG = "generic"

EXECUTION_GRAPH = """
A-0-0 A-0-1
A-0-0 A-1-0
A-0-1 A-1-1
"""

INPUTS = {
    "A-0-0": {},
    "A-0-1": {},
    "A-1-0": {'0': {'trigger_in': {'A-0.0': 0}}},
    "A-1-1": {'0': {'trigger_in': {'A-0.0': 1}}},
}

UNTIL = 2