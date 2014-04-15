"""
Scenario 6

         B(1)
       ↗
  A(1) ⇄ C(2)

"""


def create_scenario(world):
    exsim_a = world.start('A', step_size=1)
    exsim_b = world.start('B', step_size=1)
    exmas = world.start('MAS', step_size=2)
    a = exsim_a.A(init_val=0)
    b = exsim_b.B(init_val=0)
    c = exmas.Agent()
    world.connect(a[0], b[0], ('val_out', 'val_in'))
    world.connect(a[0], c[0])  # TODO: add "async_req flag"


execution_graph = """
A-0-0 A-0-1
A-0-0 B-0-0
A-0-0 MAS-0-0
A-0-1 A-0-2
A-0-1 B-0-1
A-0-2 B-0-2
A-0-2 MAS-0-2
B-0-0 B-0-1
B-0-1 B-0-2
MAS-0-0 MAS-0-2
"""
# TODO: add:
# C-0-0 B-0-0
# C-0-2 B-0-2

inputs = {
    'B-0-0': {'0.0': {'val_in': [1]}},
    'B-0-1': {'0.0': {'val_in': [2]}},
    'B-0-2': {'0.0': {'val_in': [3]}},
}

until = 3
