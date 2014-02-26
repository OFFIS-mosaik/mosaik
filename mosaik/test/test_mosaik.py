"""
Test a complete mosaik simulation using mosaik as a library.

"""
import importlib

import networkx as nx
import pytest

from mosaik import scenario


sim_config_local = {
    char: {'python': 'example_sim.mosaik:ExampleSim'} for char in 'ABCDE'
}
sim_config_remote = {
    char: {'cmd': 'pyexamplesim %(addr)s'} for char in 'ABCDE'
}


# Test all combinations of both sim configs and the 5 test scenarios.
@pytest.mark.parametrize(('fixture', 'sim_config'), [
    ('scenario_%s' % (i + 1), sc)
    for sc in [sim_config_local, sim_config_remote]
    for i in range(5)
])
def test_mosaik(fixture, sim_config):
    fixture = importlib.import_module('mosaik.test.fixtures.%s' % fixture)
    world = scenario.World(sim_config, execution_graph=True)
    fixture.create_scenario(world)
    world.run(until=fixture.until)

    expected_graph = nx.parse_edgelist(fixture.execution_graph.split('\n'),
                                       create_using=nx.DiGraph(),
                                       data=())
    for node, inputs in fixture.inputs.items():
        expected_graph.add_node(node, inputs=inputs)

    assert world.execution_graph.adj == expected_graph.adj

    for node, data in world.execution_graph.node.items():
        # Sort lists of inputs for the assertions:
        for eid, attrs in data['inputs'].items():
            for v in attrs.values():
                v.sort()

        assert data['inputs'] == expected_graph.node[node].get('inputs', {})

    for sim in world.sims.values():
        assert sim.last_step < fixture.until
        assert sim.next_step >= fixture.until
