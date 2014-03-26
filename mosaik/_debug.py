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
    def wrapped_step(env, sim, inputs):
        pre_step(env, sim, inputs)
        return _origs['step'](env, sim, inputs)

    sim.step = wrapped_step


def disable():
    """Restore all wrapped functions to their original."""
    for k, v in _origs.items():
        setattr(sim, k, v)


def pre_step(env, sim, inputs):
    """Add a node for the current step and edges from all dependencies to the
    :attr:`mosaik.scenario.Environment.execution_graph`.

    Also perform some checks and annotate the graph with the dataflows.

    """
    eg = env.execution_graph
    sims = env.sims

    sid = sim.sid
    next_step = sim.next_step
    node = '%s-%s'
    node_id = node % (sid, next_step)

    eg.add_node(node_id, t=perf_counter(), inputs=inputs)
    if sim.last_step >= 0:
        eg.add_edge(node % (sid, sim.last_step), node_id)

    for pre in env.df_graph.predecessors_iter(sid):
        pre_node = node % (pre, sims[pre].last_step)
        eg.add_edge(pre_node, node_id)
        assert eg.node[pre_node]['t'] <= eg.node[node_id]['t']

    next_steps = []
    for suc in env.df_graph.successors_iter(sid):
        suc_id = node % (suc, sims[suc].next_step)
        next_steps.append(sims[suc].next_step)

    # The next step of at least one successor must be >= our next_step (that
    # we are going to execute).
    if next_steps:
        assert max(next_steps) >= next_step, (
            '"next_step" of all successors is < "%s".next_step' % sid)
