"""
Scenario 3::

    A(2) → B(1)

"""


def create_scenario(world):
    exsim_a = world.start('A', step_size=2)
    exsim_b = world.start('B')
    a = exsim_a.A(init_val=0)
    b = exsim_b.B(init_val=0)
    world.connect(a[0], b[0], ('val_out', 'val_in'))


execution_graph = """
A-0-0 A-0-2
A-0-0 B-0-0
A-0-0 B-0-1
A-0-2 B-0-2
B-0-0 B-0-1
B-0-1 B-0-2
"""

inputs = {
    'B-0-0': {'0.0': {'val_in': [2]}},
    'B-0-1': {'0.0': {'val_in': [2]}},
    'B-0-2': {'0.0': {'val_in': [4]}},
}

until = 3
