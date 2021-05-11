"""
Test a complete mosaik simulation using mosaik as a library.

"""
import importlib
import glob
import os
import time

import networkx as nx
import pytest

from mosaik import scenario

sim_config = {
    'local': {
        **{char: {'python': 'example_sim.mosaik:ExampleSim'} for char in 'ABCDE'},
        'MAS': {'python': 'example_mas.mosaik:ExampleMas'}
    },
    'remote': {
        **{char: {'cmd': 'pyexamplesim %(addr)s'} for char in 'ABCDE'},
        'MAS': {'cmd': 'pyexamplemas %(addr)s'}
    },
    'generic': {
        **{char: {'python': 'tests.simulators.generic_test_simulator:TestSim'}
        for char in 'ABCDE'},
        'LoopSim': {
            'python': 'tests.simulators.loop_simulators.loop_simulator:LoopSim',
        },
    },
    'generic_remote': {
        char: {'cmd': '%(python)s tests/simulators/generic_test_simulator.py %(addr)s'}
        for char in 'ABCDE'
    },
    'loop': {
        'LoopSim': {
            'python': 'tests.simulators.loop_simulators.loop_simulator:LoopSim',
        },
        'EchoSim': {
            'python': 'tests.simulators.loop_simulators.echo_simulator:EchoSim',
        },
    }
}

# We test most scenarios with local simulators and only the most complex ones
# and where it is necessary with remote simulators to save some time (starting
# procs is quite expensive).

test_cases = [os.path.basename(file).strip('.py')
              for file in glob.glob('tests/fixtures/scenario_*.py')]


@pytest.mark.parametrize('fixture', test_cases)
@pytest.mark.parametrize('cache', [True, False])
def test_mosaik(fixture, cache):
    fixture = importlib.import_module('tests.fixtures.%s' % fixture)
    world = scenario.World(sim_config[fixture.CONFIG], debug=True, cache=cache)
    try:
        fixture.create_scenario(world)
        if not hasattr(fixture, 'RT_FACTOR'):
            world.run(until=fixture.UNTIL)
        else:
            world.run(until=fixture.UNTIL, rt_factor=fixture.RT_FACTOR)

        expected_graph = nx.parse_edgelist(fixture.EXECUTION_GRAPH.split('\n'),
                                           create_using=nx.DiGraph(), data=())
        for node, inputs in fixture.INPUTS.items():
            expected_graph.add_node(node, inputs=inputs)

        print(world.execution_graph.adj)
        assert world.execution_graph.adj == expected_graph.adj

        for node, data in world.execution_graph.nodes.items():
            assert data['inputs'] == expected_graph.nodes[node].get(
                'inputs', {})

        for sim in world.sims.values():
            assert sim.last_step < fixture.UNTIL
            assert sim.progress >= fixture.UNTIL - 1
    finally:
        world.shutdown()


@pytest.mark.parametrize('sim_config', [sim_config['local'], sim_config['remote']])
def test_call_extra_methods(sim_config):
    world = scenario.World(sim_config)
    try:
        model_a = world.start('A')
        ret = model_a.example_method(23)
    finally:
        world.shutdown()

    assert ret == 23


def test_rt_sim():
    fixture = importlib.import_module('tests.fixtures.scenario_1')
    world = scenario.World(sim_config['local'])
    try:
        fixture.create_scenario(world)

        factor = 0.1
        start = time.perf_counter()
        world.run(until=fixture.UNTIL, rt_factor=factor)
        duration = (time.perf_counter() - start) / factor

        assert (fixture.UNTIL - 1) < duration < fixture.UNTIL
    finally:
        world.shutdown()


@pytest.mark.parametrize('strict', [True, False])
def test_rt_sim_too_slow(strict, capsys):
    fixture = importlib.import_module('tests.fixtures.scenario_1')
    world = scenario.World(sim_config['local'])
    try:
        fixture.create_scenario(world)

        factor = 0.00001
        if strict:
            pytest.raises(RuntimeError, world.run, until=fixture.UNTIL,
                          rt_factor=factor, rt_strict=strict)
        else:
            world.run(until=fixture.UNTIL, rt_factor=factor, rt_strict=strict)
            out, err = capsys.readouterr()
            assert 'too slow for real-time factor' in out
    finally:
        world.shutdown()
