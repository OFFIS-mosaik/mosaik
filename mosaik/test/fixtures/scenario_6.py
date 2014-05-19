"""
Scenario 6

       ⇄ B(1)
  A(2) ⇄ C(2)
       ⇄ D(3)

"""


def create_scenario(world):
    exsim_a = world.start('A', step_size=2)
    exmas_b = world.start('MAS', step_size=1)
    exmas_c = world.start('MAS', step_size=2)
    exmas_d = world.start('MAS', step_size=3)
    a = exsim_a.B(init_val=0)
    b = exmas_b.Agent()
    c = exmas_c.Agent()
    d = exmas_d.Agent()
    world.connect(a, b, async_requests=True)
    world.connect(a, c, async_requests=True)
    world.connect(a, d, async_requests=True)


# A 0-----2-----4 [0, 2)
# B 0--1--2--3--4 [1, 2)
# C 0-----2-----4 [0, 2)
# D 0--------3--- [0, 3)
execution_graph = """
A-0-0 A-0-2
A-0-0 MAS-0-0
A-0-0 MAS-0-1
A-0-0 MAS-1-0
A-0-0 MAS-2-0
A-0-2 A-0-4
A-0-2 MAS-0-2
A-0-2 MAS-0-3
A-0-2 MAS-1-2
A-0-2 MAS-2-3
A-0-4 MAS-0-4
A-0-4 MAS-1-4
MAS-0-0 MAS-0-1
MAS-0-1 A-0-2
MAS-0-1 MAS-0-2
MAS-0-2 MAS-0-3
MAS-0-3 A-0-4
MAS-0-3 MAS-0-4
MAS-1-0 A-0-2
MAS-1-0 MAS-1-2
MAS-1-2 A-0-4
MAS-1-2 MAS-1-4
MAS-2-0 A-0-2
MAS-2-0 MAS-2-3
MAS-2-3 A-0-4
"""

inputs = {
    'A-0-0': {},  # Initially, there cannot be any inputs.
    'A-0-2': {'0.0': {'val_in': [23]}},
    'A-0-4': {'0.0': {'val_in': [23]}},
}

until = 5
