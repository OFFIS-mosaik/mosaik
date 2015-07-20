"""
Test a complete mosaik simulation using mosaik as a library.

"""
import importlib
import time

import networkx as nx
import pytest

from mosaik import scenario


sim_config_local = {
    char: {'python': 'example_sim.mosaik:ExampleSim'} for char in 'ABCDE'
}
sim_config_local['MAS'] = {'python': 'example_mas.mosaik:ExampleMas'}
sim_config_remote = {
    char: {'cmd': 'pyexamplesim %(addr)s'} for char in 'ABCDE'
}
sim_config_remote['MAS'] = {'cmd': 'pyexamplemas %(addr)s'}

# We test all scenarios with local simulators and only the most complex one
# with remote simulators to save some time (starting procs is quite expensive).
test_cases = [('scenario_%s' % (i + 1), sim_config_local) for i in range(6)]
test_cases.append(('scenario_5', sim_config_remote))
test_cases.append(('scenario_6', sim_config_remote))


# Test all combinations of both sim configs and the 5 test scenarios.
@pytest.mark.parametrize(('fixture', 'sim_config'), test_cases)
def test_mosaik(fixture, sim_config):
    fixture = importlib.import_module('tests.fixtures.%s' % fixture)
    world = scenario.World(sim_config, debug=True)
    fixture.create_scenario(world)
    world.run(until=fixture.until)

    expected_graph = nx.parse_edgelist(fixture.execution_graph.split('\n'),
                                       create_using=nx.DiGraph(),
                                       data=())
    for node, inputs in fixture.inputs.items():
        expected_graph.add_node(node, inputs=inputs)

    print(world.execution_graph.adj)
    assert world.execution_graph.adj == expected_graph.adj

    for node, data in world.execution_graph.node.items():
        assert data['inputs'] == expected_graph.node[node].get('inputs', {})

    for sim in world.sims.values():
        assert sim.last_step < fixture.until


@pytest.mark.parametrize('sim_config', [sim_config_local, sim_config_remote])
def test_call_extra_methods(sim_config):
    world = scenario.World(sim_config)
    try:
        A = world.start('A')
        ret = A.example_method(23)
    finally:
        world.shutdown()

    assert ret == 23


def test_rt_sim():
    fixture = importlib.import_module('tests.fixtures.scenario_1')
    world = scenario.World(sim_config_local)
    fixture.create_scenario(world)

    factor = 0.1
    start = time.perf_counter()
    world.run(until=fixture.until, rt_factor=factor)
    duration = (time.perf_counter() - start) / factor

    assert (fixture.until - 1) < duration < fixture.until


@pytest.mark.parametrize('strict', [True, False])
def test_rt_sim_too_slow(strict, capsys):
    fixture = importlib.import_module('tests.fixtures.scenario_1')
    world = scenario.World(sim_config_local)
    fixture.create_scenario(world)

    factor = 0.00001
    if strict:
        pytest.raises(RuntimeError, world.run, until=fixture.until,
                      rt_factor=factor, rt_strict=strict)
    else:
        world.run(until=fixture.until, rt_factor=factor, rt_strict=strict)
        out, err = capsys.readouterr()
        assert 'too slow for real-time factor' in out
