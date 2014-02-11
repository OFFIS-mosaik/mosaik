"""
Test a complete mosaik simulation using mosaik as a library.

"""
import networkx as nx
import pytest

from mosaik import scenario


sim_config = {
    'A': {'python': 'example_sim.mosaik:ExampleSim'},
}


def scenario_1(env):
    exsim = env.start('A')
    a = exsim.A(init_val=0)


res_1 = """
A-0 A-1
A-1 A-2
"""

scenarios = [
    (scenario_1, 3, res_1),
]


@pytest.mark.parametrize(('create_scenario', 'until', 'expected'), scenarios)
def test_mosaik(create_scenario, until, expected):
    env = scenario.Environment(sim_config)
    create_scenario(env)
    env.run(until=until)

    expected_graph = nx.parse_edgelist(expected.split('\n'),
                                       create_using=nx.DiGraph(),
                                       data=())
    assert env.result_graph.adj == expected_graph.adj
    assert env.simpy_env.now == until
    for sim in env.sims.values():
        assert sim.time < until
        assert sim.next_time >= until
    # TODO: Check progress


def create_scenario(env):
    exsim1 = env.start('PyExampleSim')
    exsim2 = env.start('PyExampleSim')

    a = [exsim1.A(init_val=0) for i in range(3)]
    b = exsim2.B.create(2, init_val=0)

    for i, j in zip(a, b):
        env.connect(i, j, ('val_out', 'val_in'))
    # env.connect((0, 1), a, b)
