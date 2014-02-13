"""
Test a complete mosaik simulation using mosaik as a library.

"""
import networkx as nx
import pytest

from mosaik import scenario


sim_config = {
    char: {'python': 'example_sim.mosaik:ExampleSim'} for char in 'ABCDE'
}


#
# Test fixtures
#
# The nodes in the scenario description below are "Simulator(resolution)"

# Scenario 1:
#
#   A(1)
#
def scenario_1(env):
    exsim = env.start('A')
    exsim.A(init_val=0)


res_1 = """
A-0-0 A-0-1
A-0-1 A-0-2
"""


# Scenario 2:
#
#  A(1) → B(1)
#
def scenario_2(env):
    exsim_a = env.start('A')
    exsim_b = env.start('B')
    a = exsim_a.A(init_val=0)
    b = exsim_b.B(init_val=0)
    env.connect(a, b, ('val_out', 'val_in'))


res_2 = """
A-0-0 A-0-1
A-0-0 B-0-0
B-0-0 B-0-1
A-0-1 B-0-1
"""


# Scenario 3:
#
#   A(2) → B(1)
#


# Scenario 4
#
#   A(1) → B(2)
#


# Scenario 5
#
# A(1) ↘      ↗ C(1)
#        B(2)
# D(4) ↗      ↘ E(3)
#


# Scenario 6
#
#        B(5)
#      ↗
# A(1) ⇄ C(1)
#

scenarios = [
    (scenario_1, 3, res_1),
    (scenario_2, 2, res_2),
]


#
# Actual tests
#
@pytest.mark.parametrize(('create_scenario', 'until', 'expected'), scenarios)
def test_mosaik(create_scenario, until, expected):
    env = scenario.Environment(sim_config, execution_graph=True)
    create_scenario(env)
    env.run(until=until)

    expected_graph = nx.parse_edgelist(expected.split('\n'),
                                       create_using=nx.DiGraph(),
                                       data=())

    print(env.execution_graph.edges())
    assert env.execution_graph.adj == expected_graph.adj

    for sim in env.sims.values():
        assert sim.last_step < until
        assert sim.next_step >= until
