"""
Test a complete mosaik simulation using mosaik as a library.

"""
import importlib
import gc
import glob
import os
import sys
import time
from types import ModuleType
from typing import Any, Dict, List, Tuple
import warnings

from loguru import logger
import networkx as nx
import pytest
from tqdm import tqdm

from mosaik import scenario, _debug
from mosaik.dense_time import DenseTime
from mosaik.tiered_time import TieredTime

VENV = os.path.dirname(sys.executable)

SIM_CONFIG: Dict[str, scenario.SimConfig] = {
    'local': {
        **{char: {'python': 'example_sim.mosaik:ExampleSim'} for char in 'ABCDE'},
        'MAS': {'python': 'example_mas.mosaik:ExampleMas'}
    },
    'remote': {
        **{
            char: {'cmd': f'{VENV}/pyexamplesim %(addr)s'}
            for char in 'ABCDE'
        },
        'MAS': {'cmd': f'{VENV}/pyexamplemas %(addr)s'}
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

test_cases: List[Any] = []
for file in os.listdir('tests/scenarios'):
    if not file.startswith('__'):
        scenario_name = os.path.basename(file)[0:-3]  # remove ".py" at the end
        scenario_desc = importlib.import_module(f"tests.scenarios.{scenario_name}")
        test_cases.append(
            pytest.param(scenario_desc, marks=[
                *([pytest.mark.weak] if getattr(scenario_desc, "WEAK", False) else []),
            ])
        )


@pytest.mark.filterwarnings("ignore:Connections with async_requests")
@pytest.mark.parametrize('scenario_desc', test_cases)
@pytest.mark.parametrize('cache', [True, False])
def test_mosaik(scenario_desc: ModuleType, cache: bool):
    logger.remove()
    logger.add(lambda msg: tqdm.write(msg, end=""), colorize=True)
    if cache in getattr(scenario_desc, 'SKIP', []):
        pytest.skip()
    if cache in getattr(scenario_desc, 'XFAIL', []):
        pytest.xfail()
    world = scenario.World(SIM_CONFIG[scenario_desc.CONFIG], debug=True, cache=cache)
    try:
        scenario_desc.create_scenario(world)
        world.run(
            until=scenario_desc.UNTIL,
            rt_factor=getattr(scenario_desc, "RT_FACTOR", None),
            print_progress=False,
        )

        expected_graph = _debug.parse_execution_graph(scenario_desc.EXECUTION_GRAPH)
        
        for node, inputs in scenario_desc.INPUTS.items():
            expected_graph.add_node(_debug.parse_node(node), inputs=inputs)

        errors: List[str] = []
        expected_nodes = set(expected_graph.nodes)
        actual_nodes = set(world.execution_graph.nodes)
        missing_nodes = expected_nodes - actual_nodes

        def format_node(node: Tuple[str, TieredTime]) -> str:
            return f"{node[0]} @ {node[1]}"
        
        if missing_nodes:
            errors.append("The following expected simulator invocations did not happen:")
            for node in sorted(missing_nodes, key=lambda n: n[0]):
                errors.append(f"- {format_node(node)}")
            errors.append("")

        extra_nodes = actual_nodes - expected_nodes
        if extra_nodes:
            errors.append("The following simulator invocations were not expected:")
            for node in sorted(extra_nodes, key=lambda n: n[0]):
                sources = world.execution_graph.predecessors(node)
                if sources:
                    sources_str = f"caused by: {', '.join(map(format_node, sources))}"
                else:
                    sources_str = "not caused by other simulators"
                errors.append(f"- {format_node(node)} ({sources_str})")
            errors.append("")

        predecessor_errors: List[str] = []
        for node in sorted(actual_nodes & expected_nodes):
            actual_pres = set(world.execution_graph.predecessors(node))
            expected_pres = set(expected_graph.predecessors(node))
            if actual_pres != expected_pres:
                predecessor_errors.append(
                    f"- {format_node(node)} ("
                    f"extraneous {', '.join(map(format_node, sorted(actual_pres - expected_pres)))}; "
                    f"missing {', '.join(map(format_node, sorted(expected_pres - actual_pres)))})"
                )
        if predecessor_errors:
            errors.append(
                "The following simulator invocations had incorrect sources:"
            )
            errors.extend(predecessor_errors)
            errors.append("")

        if errors:
            raise AssertionError(
                "The following problems were detected in the execution graph:\n\n"
                + "\n".join(errors)
            )
            
        assert world.execution_graph.adj == expected_graph.adj

        for node, data in world.execution_graph.nodes.items():
            assert data['inputs'] == expected_graph.nodes[node].get(
                'inputs', {}), f"Inputs for {format_node(node)}"

        for sim in world.sims.values():
            assert sim.last_step.time < scenario_desc.UNTIL
            assert sim.progress.time.time == scenario_desc.UNTIL
    finally:
        world.shutdown()
        gc.collect()


@pytest.mark.parametrize('sim_config', [SIM_CONFIG['local'], SIM_CONFIG['remote']])
def test_call_extra_methods(sim_config):
    world = scenario.World(sim_config)
    try:
        model_a = world.start('A')
        ret = model_a.example_method(23)
    finally:
        world.shutdown()

    assert ret == 23


@pytest.mark.parametrize('sim_config', [SIM_CONFIG['generic'], SIM_CONFIG['generic_remote']])
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
    world = scenario.World(SIM_CONFIG['local'])
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
    world = scenario.World(SIM_CONFIG['local'])
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
