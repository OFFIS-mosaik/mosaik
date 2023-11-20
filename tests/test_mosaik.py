"""
Test a complete mosaik simulation using mosaik as a library.

"""
import importlib
import gc
import glob
import os
import time
from typing import Dict, List
import warnings

from loguru import logger
import networkx as nx
import pytest
from tqdm import tqdm

from mosaik import scenario


sim_config: Dict[str, scenario.SimConfig] = {
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
        'FixedOut': {'python': 'tests.simulators.fixed_output_sim:FixedOutputSim'},
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

test_cases = [os.path.basename(file)[0:-3]  # remove ".py" at the end
              for file in os.listdir('tests/scenarios')
              if not file.startswith('__')]


@pytest.mark.filterwarnings("ignore:Connections with async_requests")
@pytest.mark.parametrize('scenario_name', test_cases)
@pytest.mark.parametrize('cache', [True, False])
def test_mosaik(scenario_name: str, cache: bool):
    logger.remove()
    logger.add(lambda msg: tqdm.write(msg, end=""), colorize=True)
    scenario_desc = importlib.import_module(f'tests.scenarios.{scenario_name}')
    if hasattr(scenario_desc, 'SKIP') and cache in scenario_desc.SKIP:
        pytest.skip()
    if hasattr(scenario_desc, 'XFAIL') and cache in scenario_desc.XFAIL:
        pytest.xfail()
    world = scenario.World(sim_config[scenario_desc.CONFIG], debug=True, cache=cache)
    try:
        scenario_desc.create_scenario(world)
        if not hasattr(scenario_desc, 'RT_FACTOR'):
            world.run(until=scenario_desc.UNTIL)
        else:
            world.run(until=scenario_desc.UNTIL, rt_factor=scenario_desc.RT_FACTOR)

        expected_graph = nx.parse_edgelist(
            scenario_desc.EXECUTION_GRAPH.split('\n'),
            create_using=nx.DiGraph(),
            data=()
        )
        
        for node, inputs in scenario_desc.INPUTS.items():
            expected_graph.add_node(node, inputs=inputs)

        errors: List[str] = []
        expected_nodes = set(expected_graph.nodes)
        actual_nodes = set(world.execution_graph.nodes)
        missing_nodes = expected_nodes - actual_nodes
        if missing_nodes:
            errors.append("The following expected simulator invocations did not happen:")
            for node in sorted(missing_nodes):
                errors.append(f"- {node}")
            errors.append("\n")

        extra_nodes = set(
            n
            for n in actual_nodes - expected_nodes
            if "inputs" in world.execution_graph[n]
        )
        if extra_nodes:
            errors.append("The following simulator invocations were not expected:")
            for node in sorted(extra_nodes):
                sources = world.execution_graph.predecessors(node)
                if sources:
                    sources_str = f"caused by: {', '.join(sources)}"
                else:
                    sources_str = "not caused by other simulators"
                errors.append(f"- {node} ({sources_str})")
            errors.append("\n")

        predecessor_errors: List[str] = []
        for node in sorted(actual_nodes & expected_nodes):
            actual_pres = set(world.execution_graph.predecessors(node))
            expected_pres = set(expected_graph.predecessors(node))
            if actual_pres != expected_pres:
                predecessor_errors.append(
                    f"- {node} ("
                    f"extraneous {', '.join(sorted(actual_pres - expected_pres))}; "
                    f"missing {', '.join(sorted(expected_pres - actual_pres))})"
                )
        if predecessor_errors:
            errors.append(
                "The following simulator invocations had incorrect sources:"
            )
            errors.extend(predecessor_errors)
            errors.append("\n")

        if errors:
            raise AssertionError(
                "The following problems were detected in the execution graph:\n\n"
                + "\n".join(errors)
            )
            
        for node, data in world.execution_graph.nodes.items():
            assert data['inputs'] == expected_graph.nodes[node].get(
                'inputs', {}), f"Inputs for {node}"

        for sim in world.sims.values():
            assert sim.last_step.time < scenario_desc.UNTIL
            assert sim.progress.value.time == scenario_desc.UNTIL
    finally:
        world.shutdown()
        gc.collect()


@pytest.mark.parametrize('sim_config', [sim_config['local'], sim_config['remote']])
def test_call_extra_methods(sim_config):
    world = scenario.World(sim_config)
    try:
        model_a = world.start('A')
        ret = model_a.example_method(23)
    finally:
        world.shutdown()

    assert ret == 23


@pytest.mark.parametrize('sim_config', [sim_config['generic'], sim_config['generic_remote']])
def test_call_two_extra_methods(sim_config):
    world = scenario.World(sim_config)
    try:
        model_a = world.start('A')
        ret_a1 = model_a.method_a(arg=23)
        ret_a2 = model_a.method_a(882)
        ret_b = model_a.method_b(val=42)
    finally:
        world.shutdown()

    assert ret_a1 == "method_a(23)"
    assert ret_a2 == "method_a(882)"
    assert ret_b == "method_b(42)"


def test_rt_sim():
    fixture = importlib.import_module('tests.scenarios.single_self_stepping')
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
def test_rt_sim_too_slow(strict, caplog):
    fixture = importlib.import_module('tests.scenarios.single_self_stepping')
    world = scenario.World(sim_config['local'])
    try:
        fixture.create_scenario(world)

        factor = 0.00001
        if strict:
            pytest.raises(RuntimeError, world.run, until=fixture.UNTIL,
                          rt_factor=factor, rt_strict=strict)
        else:
            world.run(until=fixture.UNTIL, rt_factor=factor, rt_strict=strict)
            assert 'too slow for real-time factor' in caplog.text
    finally:
        world.shutdown()
