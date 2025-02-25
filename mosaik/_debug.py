"""
This module allows you to activate some debugging functionality that
makes mosaik collect more data when the simulation is being executed.
"""

from __future__ import annotations

from copy import deepcopy
from time import perf_counter
from typing import Dict, List, Optional, Tuple

import networkx as nx
from loguru import logger  # noqa: F401  # type: ignore
from mosaik_api_v3 import InputData, SimId

from mosaik import AsyncWorld, scheduler
from mosaik.scenario import World
from mosaik.simmanager import SimRunner
from mosaik.tiered_time import TieredDuration, TieredTime

_originals = {
    "step": scheduler.step,
}


def enable():
    """
    Wrap :func:`~mosaik.scheduler.step()` to collect more data about the
    scheduler execution.
    """

    async def wrapped_step(
        world: AsyncWorld, sim: SimRunner, inputs: InputData, max_advance: int
    ):
        pre_step(world, sim, inputs)
        ret = await _originals["step"](world, sim, inputs, max_advance)
        post_step(world, sim)
        return ret

    scheduler.step = wrapped_step
    World.assert_graph = assert_graph
    World.assert_inputs = assert_inputs


def disable():
    """
    Restore all wrapped functions to their original.
    """
    for k, v in _originals.items():
        setattr(scheduler, k, v)


def parse_node(node_str: str) -> Tuple[SimId, TieredTime]:
    # networkx will call the parser on already-parsed nodes occasionally
    # So we make sure that we only try to parse strings.
    if isinstance(node_str, str):
        sid, time = node_str.rsplit("~", 1)
        return (sid, TieredTime(*tuple(map(int, time.split(":")))))
    return node_str


def parse_execution_graph(graph_string: str) -> nx.DiGraph[Tuple[SimId, TieredTime]]:
    return nx.parse_edgelist(
        graph_string.split("\n"),
        create_using=nx.DiGraph(),
        nodetype=parse_node,
        data=(),
    )


def pre_step(world: AsyncWorld, sim: SimRunner, inputs: InputData):
    """
    Add a node for the current step and edges from all dependencies to
    the :attr:`mosaik.scenario.World.execution_graph`.

    Also perform some checks and annotate the graph with the dataflows.
    """
    eg = world.execution_graph
    sims = world.sims

    sid = sim.sid
    assert sim.current_step is not None
    next_step = sim.current_step
    node_id = (sid, next_step)

    sim.last_node = node_id

    eg.add_node(node_id, t=perf_counter(), inputs=deepcopy(inputs))

    input_pres = {
        kk.split(".")[0]
        for ii in inputs.values()
        for jj in ii.values()
        for kk in jj.keys()
    }
    for pre_sim, min_delays in sim.input_delays.items():
        if pre_sim.sid in input_pres or sim in pre_sim.successors_to_wait_for:
            pre_node: Optional[Tuple[str, TieredTime]] = None
            pre_time = TieredTime(-1, *([0] * (len(pre_sim.progress.time) - 1)))
            # We check for all nodes if it is from the predecessor and
            # it its step time is before the current step of sim. There
            # might be cases where this simple procedure is wrong, e.g.
            # when the pred has stepped but didn't provide the connected
            # output.
            for inode in eg.nodes:
                node_sid, itime = inode
                if (
                    node_sid == pre_sim.sid
                    and next_step >= min_delays.earliest_sum(itime)
                    and itime >= pre_time
                ):
                    pre_node = inode
                    pre_time = itime
            if pre_node is not None:
                eg.add_edge(pre_node, node_id)
                assert eg.nodes[pre_node]["t"] <= eg.nodes[node_id]["t"]

    for suc_sim in sim.successors_to_wait_for:
        suc = suc_sim.sid
        if sim.last_step >= TieredTime(0):
            suc_node = (suc, sims[suc].last_step)
            eg.add_edge(suc_node, node_id)
            assert sims[suc].progress.time + TieredDuration(1) >= next_step


def post_step(world: AsyncWorld, sim: SimRunner):
    """
    Record time after a step and add self-step edge.
    """
    eg = world.execution_graph
    last_node = sim.last_node
    eg.nodes[last_node]["t_end"] = perf_counter()
    next_self_step = sim.next_self_step
    if (
        next_self_step is not None
        and next_self_step < TieredTime(world.until) + sim.from_world_time
    ):
        node_id = (sim.sid, next_self_step)
        eg.add_edge(sim.last_node, node_id)
        sim.next_self_step = None


def assert_graph(world: AsyncWorld, expected_str: str, extra_nodes: List[str] = []):  # noqa: C901
    actual_graph = world.execution_graph
    expected_graph = parse_execution_graph(expected_str)
    for node in extra_nodes:
        expected_graph.add_node(parse_node(node))

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

    unexpected_nodes = actual_nodes - expected_nodes
    if unexpected_nodes:
        errors.append("The following simulator invocations were not expected:")
        for node in sorted(unexpected_nodes):
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
            extraneous = ", ".join(
                map(format_node, sorted(actual_pres - expected_pres))
            )
            missing = ", ".join(map(format_node, sorted(expected_pres - actual_pres)))
            predecessor_errors.append(
                f"- {format_node(node)} (extraneous {extraneous}; missing {missing})"
            )
    if predecessor_errors:
        errors.append("The following simulator invocations had incorrect sources:")
        errors.extend(predecessor_errors)
        errors.append("")

    if errors:
        raise AssertionError(
            "The following problems were detected in the execution graph:\n\n"
            + "\n".join(errors)
        )

    assert actual_graph.adj == expected_graph.adj


def assert_inputs(world: AsyncWorld, expected_inputs: Dict[str, InputData]):
    eg = world.execution_graph
    for node_str, expected_data in expected_inputs.items():
        node = parse_node(node_str)
        assert expected_data == eg.nodes[node]["inputs"]
        del eg.nodes[node]["inputs"]
    for node in eg.nodes(data="inputs"):
        assert not node[1]  # Make sure that there are not unchecked inputs
