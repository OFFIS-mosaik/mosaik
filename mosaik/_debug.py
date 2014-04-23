"""
This module allows you to activate some debugging functionality that makes
mosaik collect more data when the simulation is being executed.

"""
from time import perf_counter

import mosaik.simulator as sim


_origs = {
    'step': sim.step,
}


def enable():
    """Wrap :func:`~mosaik.simulator.step()` to collect more data about the
    simulation execution.

    """
    def wrapped_step(world, sim, inputs):
        pre_step(world, sim, inputs)
        return _origs['step'](world, sim, inputs)

    sim.step = wrapped_step


def disable():
    """Restore all wrapped functions to their original."""
    for k, v in _origs.items():
        setattr(sim, k, v)


def pre_step(world, sim, inputs):
    """Add a node for the current step and edges from all dependencies to the
    :attr:`mosaik.scenario.World.execution_graph`.

    Also perform some checks and annotate the graph with the dataflows.

    """
    eg = world.execution_graph
    sims = world.sims

    sid = sim.sid
    next_step = sim.next_step
    node = '%s-%s'
    node_id = node % (sid, next_step)
    # print('###', node_id)

    eg.add_node(node_id, t=perf_counter(), inputs=inputs)
    if sim.last_step >= 0:
        eg.add_edge(node % (sid, sim.last_step), node_id)

    for pre in world.df_graph.predecessors_iter(sid):
        pre_node = node % (pre, sims[pre].last_step)
        eg.add_edge(pre_node, node_id)
        assert eg.node[pre_node]['t'] <= eg.node[node_id]['t']

    next_steps = []
    for suc in world.df_graph.successors_iter(sid):
        if world.df_graph[sid][suc]['async_requests'] and sim.last_step >= 0:
            suc_node = node % (suc, sims[suc].last_step)
            eg.add_edge(suc_node, node_id)
            assert sims[suc].next_step >= next_step
        next_steps.append(sims[suc].next_step)

    # The next step of at least one successor must be >= our next_step (that
    # we are going to execute).
    if next_steps:
        assert max(next_steps) >= next_step, (
            '"next_step" of all successors of "%s" is < %s' % (sid, next_step))
