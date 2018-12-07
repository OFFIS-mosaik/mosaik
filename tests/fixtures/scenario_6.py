"""
Scenario 6

       ⇄ B(1)
  A(2) ⇄ C(2)
       ⇄ D(3)
"""


def create_scenario(world):
    simulator_a = world.start('A', step_size=2)
    mas_b = world.start('MAS', step_size=1)
    mas_c = world.start('MAS', step_size=2)
    mas_d = world.start('MAS', step_size=3)
    model_a = simulator_a.B(init_val=0)
    model_b = mas_b.Agent()
    agent_c = mas_c.Agent()
    agent_d = mas_d.Agent()
    world.connect(model_a, model_b, async_requests=True)
    world.connect(model_a, agent_c, async_requests=True)
    world.connect(model_a, agent_d, async_requests=True)


# A 0-----2-----4 [0, 2)
# B 0--1--2--3--4 [1, 2)
# C 0-----2-----4 [0, 2)
# D 0--------3--- [0, 3)
EXECUTION_GRAPH = """
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

INPUTS = {
    'A-0-0': {},  # Initially, there cannot be any inputs.
    'A-0-2': {'0.0': {'val_in': {'MAS-0.0': 23, 'MAS-1.0': 23,
                                 'MAS-2.0': 23}}},
    'A-0-4': {'0.0': {'val_in': {'MAS-0.0': 23, 'MAS-1.0': 23,
                                 'MAS-2.0': 23}}},
}

UNTIL = 5
