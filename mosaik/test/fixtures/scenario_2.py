"""
Scenario 2::

    A(1) → B(1)

"""


def create_scenario(world):
    exsim_a = world.start('A')
    exsim_b = world.start('B')
    a = exsim_a.A(init_val=0)
    b = exsim_b.B(init_val=0)
    world.connect(a, b, ('val_out', 'val_in'))


execution_graph = """
A-0-0 A-0-1
A-0-0 B-0-0
A-0-1 B-0-1
B-0-0 B-0-1
"""

inputs = {
    'B-0-0': {'0.0': {'val_in': [1]}},
    'B-0-1': {'0.0': {'val_in': [2]}},
}

until = 2
