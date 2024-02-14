"""
Scenario 6

       ⇄ B(1)
  A(2) ⇄ C(2)
       ⇄ D(3)
"""
from mosaik import World


def create_scenario(world: World):
    simulator_a = world.start('A', sim_id="A", step_size=2)
    mas_b = world.start('MAS', sim_id="B", step_size=1)
    mas_c = world.start('MAS', sim_id="C", step_size=2)
    mas_d = world.start('MAS', sim_id="D", step_size=3)
    model_a = simulator_a.B(init_val=0)
    agent_b = mas_b.Agent()
    agent_c = mas_c.Agent()
    agent_d = mas_d.Agent()
    world.connect(model_a, agent_b, async_requests=True)
    world.connect(model_a, agent_c, async_requests=True)
    world.connect(model_a, agent_d, async_requests=True)


# A 0-----2-----4 [0, 2)
# B 0--1--2--3--4 [1, 2)
# C 0-----2-----4 [0, 2)
# D 0--------3--- [0, 3)


CONFIG = 'remote'

EXECUTION_GRAPH = """
A~0 A~2
A~0 B~0
A~0 B~1
A~0 C~0
A~0 D~0
A~2 A~4
A~2 B~2
A~2 B~3
A~2 C~2
A~2 D~3
A~4 B~4
A~4 C~4
B~0 B~1
B~1 A~2
B~1 B~2
B~2 B~3
B~3 A~4
B~3 B~4
C~0 A~2
C~0 C~2
C~2 A~4
C~2 C~4
D~0 A~2
D~0 D~3
D~3 A~4
"""

INPUTS = {
    'A~0': {},  # Initially, there cannot be any inputs.
    'A~2': {'0.0': {'val_in': {'B.0': 23, 'C.0': 23,
                                 'D.0': 23}}},
    'A~4': {'0.0': {'val_in': {'B.0': 23, 'C.0': 23,
                                 'D.0': 23}}},
}

UNTIL = 5
