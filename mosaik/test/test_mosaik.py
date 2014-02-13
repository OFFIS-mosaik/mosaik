"""
Test a complete mosaik simulation using mosaik as a library.

"""
import networkx as nx
import pytest

from mosaik import scenario


sim_config = {
    'A': {'python': 'example_sim.mosaik:ExampleSim'},
}


#
# Test fixtures
#

def scenario_1(env):
    exsim = env.start('A')
    a = exsim.A(init_val=0)


res_1 = nx.DiGraph([
    ('A-0-0', 'A-0-1'),
    ('A-0-1', 'A-0-2'),
])
for i in range(3):
    res_1.add_node('A-0-%d' % i, st=i)


scenarios = [
    (scenario_1, 3, res_1),
]

#
# Actual tests
#

@pytest.mark.parametrize(('create_scenario', 'until', 'expected'), scenarios)
def test_mosaik(create_scenario, until, expected):
    env = scenario.Environment(sim_config, execution_graph=True)
    create_scenario(env)
    env.run(until=until)

    assert env.execution_graph.adj == expected.adj
    for node, data in env.execution_graph.node.items():
        assert data['st'] == expected.node[node]['st']

    assert env.simpy_env.now == until
    for sim in env.sims.values():
        assert sim.time < until
        assert sim.next_step >= until
