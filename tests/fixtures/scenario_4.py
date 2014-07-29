"""
Scenario 4

    A(1) → B(2)

"""


def create_scenario(world):
    exsim_a = world.start('A')
    exsim_b = world.start('B', step_size=2)
    a = exsim_a.A(init_val=0)
    b = exsim_b.B(init_val=0)
    world.connect(a, b, ('val_out', 'val_in'))


execution_graph = """
A-0-0 A-0-1
A-0-0 B-0-0
A-0-1 A-0-2
A-0-2 B-0-2
B-0-0 B-0-2
"""

inputs = {
    'B-0-0': {'0.0': {'val_in': [1]}},
    'B-0-2': {'0.0': {'val_in': [3]}},
}

until = 4
