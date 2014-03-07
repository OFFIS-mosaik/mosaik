"""
Scenario 5

  A(1) ↘      ↗ C(1)
         B(2)
  D(4) ↗      ↘ E(3)

"""


def create_scenario(world):
    exsim_a = world.start('A', step_size=1)
    exsim_b = world.start('B', step_size=2)
    exsim_c = world.start('C', step_size=1)
    exsim_d = world.start('D', step_size=4)
    exsim_e = world.start('E', step_size=3)
    a = exsim_a.A(init_val=0)
    b = exsim_b.B(init_val=0)
    c = exsim_c.B(init_val=0)
    d = exsim_d.B(init_val=0)
    e = exsim_e.B(init_val=0)
    world.connect(a[0], b[0], ('val_out', 'val_in'))
    world.connect(d[0], b[0], ('val_out', 'val_in'))
    world.connect(b[0], c[0], ('val_out', 'val_in'))
    world.connect(b[0], e[0], ('val_out', 'val_in'))


execution_graph = """
A-0-0 A-0-1
A-0-0 B-0-0
A-0-1 A-0-2
A-0-2 A-0-3
A-0-2 B-0-2
A-0-3 A-0-4
A-0-4 B-0-4
B-0-0 B-0-2
B-0-0 C-0-0
B-0-0 C-0-1
B-0-0 E-0-0
B-0-2 B-0-4
B-0-2 C-0-2
B-0-2 C-0-3
B-0-2 E-0-3
B-0-4 C-0-4
C-0-0 C-0-1
C-0-1 C-0-2
C-0-2 C-0-3
C-0-3 C-0-4
D-0-0 B-0-0
D-0-0 B-0-2
D-0-0 D-0-4
D-0-4 B-0-4
E-0-0 E-0-3
"""

inputs = {
    'B-0-0': {'0.0': {'val_in': [0, 1]}},
    'B-0-2': {'0.0': {'val_in': [0, 3]}},
    'B-0-4': {'0.0': {'val_in': [0, 5]}},
    'C-0-0': {'0.0': {'val_in': [1]}},
    'C-0-1': {'0.0': {'val_in': [1]}},
    'C-0-2': {'0.0': {'val_in': [3]}},
    'C-0-3': {'0.0': {'val_in': [3]}},
    'C-0-4': {'0.0': {'val_in': [5]}},
    'E-0-0': {'0.0': {'val_in': [1]}},
    'E-0-3': {'0.0': {'val_in': [3]}},
}

until = 5
