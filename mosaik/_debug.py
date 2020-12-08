"""
This module allows you to activate some debugging functionality that makes
mosaik collect more data when the simulation is being executed.
"""
from time import perf_counter

from mosaik import scheduler

_originals = {
    'step': scheduler.step,
}


def enable():
    """
    Wrap :func:`~mosaik.scheduler.step()` to collect more data about the
    scheduler execution.
    """

    def wrapped_step(world, sim, inputs, preds_progress):
        pre_step(world, sim, inputs)
        ret = yield from _originals['step'](world, sim, inputs, preds_progress)
        post_step(world, sim)
        return ret

    scheduler.step = wrapped_step


def disable():
    """
    Restore all wrapped functions to their original.
    """
    for k, v in _originals.items():
        setattr(scheduler, k, v)


def pre_step(world, sim, inputs):
    """
    Add a node for the current step and edges from all dependencies to the
    :attr:`mosaik.scenario.World.execution_graph`.

    Also perform some checks and annotate the graph with the dataflows.
    """
    eg = world.execution_graph
    dfg = world.df_graph
    sims = world.sims

    sid = sim.sid
    next_step = sim.next_step
    node = '%s-%s'
    node_id = node % (sid, next_step)

    eg.add_node(node_id, t=perf_counter(), inputs=inputs)
    if next_step == sim.next_self_step[0] and sim.last_step >= 0:
        eg.add_edge(node % (sid, sim.next_self_step[1]), node_id)

    input_pres = {kk.split('.')[0] for ii in inputs.values()
                  for jj in ii.values() for kk in jj.keys()}
    for pre in dfg.predecessors(sid):
        if pre in input_pres or dfg[pre][sid]['async_requests']:
            for inode in eg.nodes:
                node_sid, istep = inode.rsplit('-', 1)
                if node_sid == pre:
                    if int(istep) <= next_step - dfg[pre][sid]['time_shifted']:
                        pre_step = istep
                    else:
                        break
            pre_node = node % (pre, pre_step)
            eg.add_edge(pre_node, node_id)
            assert eg.nodes[pre_node]['t'] <= eg.nodes[node_id]['t']

    for suc in dfg.successors(sid):
        if dfg[sid][suc]['async_requests'] and sim.last_step >= 0:
            suc_node = node % (suc, sims[suc].last_step)
            eg.add_edge(suc_node, node_id)
            assert sims[suc].progress + 1 >= next_step


def post_step(world, sim):
    """
    Record time after a step.
    """
    eg = world.execution_graph
    sid = sim.sid
    last_step = sim.last_step
    node = '%s-%s'
    node_id = node % (sid, last_step)
    eg.nodes[node_id]['t_end'] = perf_counter()
