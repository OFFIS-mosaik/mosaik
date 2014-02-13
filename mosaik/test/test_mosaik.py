"""
Test a complete mosaik simulation using mosaik as a library.

"""
import importlib

import networkx as nx
import pytest

from mosaik import scenario


sim_config = {
    char: {'python': 'example_sim.mosaik:ExampleSim'} for char in 'ABCDE'
}


@pytest.mark.parametrize('fixture', [
    'scenario_%s' % (i + 1) for i in range(5)
])
def test_mosaik(fixture):
    fixture = importlib.import_module('mosaik.test.fixtures.%s' % fixture)
    env = scenario.Environment(sim_config, execution_graph=True)
    fixture.create_scenario(env)
    env.run(until=fixture.until)

    expected_graph = nx.parse_edgelist(fixture.execution_graph.split('\n'),
                                       create_using=nx.DiGraph(),
                                       data=())
    for node, inputs in fixture.inputs.items():
        expected_graph.add_node(node, inputs=inputs)

    assert env.execution_graph.adj == expected_graph.adj

    for node, data in env.execution_graph.node.items():
        # Sort lists of inputs for the assertions:
        for eid, attrs in data['inputs'].items():
            for v in attrs.values():
                v.sort()

        assert data['inputs'] == expected_graph.node[node].get('inputs', {})

    for sim in env.sims.values():
        assert sim.last_step < fixture.until
        assert sim.next_step >= fixture.until
