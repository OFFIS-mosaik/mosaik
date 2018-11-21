"""
Scenario 5

  A(1) ↘      ↗ C(1)
         B(2)
  D(4) ↗      ↘ E(3)
"""


def create_scenario(world):
    simulator_a = world.start('A', step_size=1)
    simulator_b = world.start('B', step_size=2)
    simulator_c = world.start('C', step_size=1)
    simulator_d = world.start('D', step_size=4)
    simulator_e = world.start('E', step_size=3)
    model_a = simulator_a.A(init_val=0)
    model_b = simulator_b.B(init_val=0)
    model_c = simulator_c.B(init_val=0)
    model_d = simulator_d.B(init_val=0)
    model_e = simulator_e.B(init_val=0)
    world.connect(model_a, model_b, ('val_out', 'val_in'))
    world.connect(model_d, model_b, ('val_out', 'val_in'))
    world.connect(model_b, model_c, ('val_out', 'val_in'))
    world.connect(model_b, model_e, ('val_out', 'val_in'))


EXECUTION_GRAPH = """
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

INPUTS = {
    'B-0-0': {'0.0': {'val_in': {'A-0.0.0': 1, 'D-0.0.0': 0}}},
    'B-0-2': {'0.0': {'val_in': {'A-0.0.0': 3, 'D-0.0.0': 0}}},
    'B-0-4': {'0.0': {'val_in': {'A-0.0.0': 5, 'D-0.0.0': 0}}},
    'C-0-0': {'0.0': {'val_in': {'B-0.0.0': 1}}},
    'C-0-1': {'0.0': {'val_in': {'B-0.0.0': 1}}},
    'C-0-2': {'0.0': {'val_in': {'B-0.0.0': 3}}},
    'C-0-3': {'0.0': {'val_in': {'B-0.0.0': 3}}},
    'C-0-4': {'0.0': {'val_in': {'B-0.0.0': 5}}},
    'E-0-0': {'0.0': {'val_in': {'B-0.0.0': 1}}},
    'E-0-3': {'0.0': {'val_in': {'B-0.0.0': 3}}},
}

UNTIL = 5
