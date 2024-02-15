import os
import sys
from typing import Dict, List, Tuple
from loguru import logger
from mosaik_api_v3 import InputData
import pytest
from tqdm import tqdm

import mosaik
from mosaik import _debug
from mosaik.tiered_time import TieredTime

venv = os.path.dirname(sys.executable)

SIM_CONFIG: mosaik.SimConfig = {
    "Local": {"python": "example_sim.mosaik:ExampleSim"},
    "LocalMAS": {"python": "example_mas.mosaik:ExampleMas"},
    "Generic": {"python": "tests.simulators.generic_test_simulator:TestSim"},
    "LoopSim": {"python": "tests.simulators.loop_simulators.loop_simulator:LoopSim"},
    "FixedOut": {"python": "tests.simulators.fixed_output_sim:FixedOutputSim"},
    "EchoSim": {"python": "tests.simulators.loop_simulators.echo_simulator:EchoSim"},

    "Remote": {"cmd": f"{venv}/pyexamplesim %(addr)s"},
    "RemoteMAS": {"cmd": f"{venv}/pyexamplemas %(addr)s"},
    "RemoteGeneric": {
        "cmd": "%(python)s tests/simulators/generic_test_simulator.py %(addr)s"
    },
}


@pytest.fixture(params=[True, False])
def world(request: pytest.FixtureRequest):
    logger.remove()
    logger.add(lambda msg: tqdm.write(msg, end=""), colorize=True)
    cache: bool = request.param
    
    world = mosaik.World(SIM_CONFIG, debug=True, cache=cache)
    yield world
    world.shutdown()


@pytest.fixture
def check(world: mosaik.World):
    yield ExecutionChecker(world)


def format_node(node: Tuple[str, TieredTime]) -> str:
    return f"{node[0]} @ {node[1]}"


class ExecutionChecker:
    world: mosaik.World

    def __init__(self, world: mosaik.World):
        self.world = world

    def graph(self, expected_str: str):
        actual_graph = self.world.execution_graph
        expected_graph = _debug.parse_execution_graph(expected_str)

        errors: List[str] = []
        expected_nodes = set(expected_graph.nodes)
        actual_nodes = set(actual_graph.nodes)
        missing_nodes = expected_nodes - actual_nodes

        def format_node(node: Tuple[str, TieredTime]) -> str:
            return f"{node[0]} @ {node[1]}"
        
        if missing_nodes:
            errors.append("The following expected simulator invocations did not happen:")
            for node in sorted(missing_nodes):
                errors.append(f"- {format_node(node)}")
            errors.append("")

        extra_nodes = actual_nodes - expected_nodes
        if extra_nodes:
            errors.append("The following simulator invocations were not expected:")
            for node in sorted(extra_nodes):
                sources = actual_graph.predecessors(node)
                if sources:
                    sources_str = f"caused by: {', '.join(map(format_node, sources))}"
                else:
                    sources_str = "not caused by other simulators"
                errors.append(f"- {format_node(node)} ({sources_str})")
            errors.append("")

        predecessor_errors: List[str] = []
        for node in sorted(actual_nodes & expected_nodes):
            actual_pres = set(actual_graph.predecessors(node))
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
            
        assert actual_graph.adj == expected_graph.adj

    def inputs(self, expected_inputs: Dict[str, InputData]):
        eg = self.world.execution_graph
        for node_str, expected_data in expected_inputs.items():
            node = _debug.parse_node(node_str)
            assert expected_data == eg.nodes[node]['inputs']
            del eg.nodes[node]['inputs']
        for node in eg.nodes(data="inputs"):
            assert not node[1]  # Make sure that there are not unchecked inputs
