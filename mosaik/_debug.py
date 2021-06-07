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

    def wrapped_step(world, sim, inputs, max_advance):
        pre_step(world, sim, inputs)
        ret = yield from _originals['step'](world, sim, inputs, max_advance)
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

    if hasattr(sim, 'last_node'):
        last_node = sim.last_node
        time_last_node = int(last_node.split('~')[0].split('-')[-1])
    else:
        time_last_node = -1

    if next_step == time_last_node:
        n_rep = int(last_node.split('~')[-1]) if '~' in last_node else 0
        node_id = f'{node_id}~{n_rep + 1}'

    sim.last_node = node_id

    eg.add_node(node_id, t=perf_counter(), inputs=inputs)

    input_pres = {kk.split('.')[0] for ii in inputs.values()
                  for jj in ii.values() for kk in jj.keys()}
    for pre in dfg.predecessors(sid):
        if pre in input_pres or dfg[pre][sid]['async_requests']:
            pre_node = None
            pre_time = -1
            # We check for all nodes if it is from the predecessor and it its
            # step time is before the current step of sim. There might be cases
            # where this simple procedure is wrong, e.g. when the pred has
            # stepped but didn't provide the connected output.
            for inode in eg.nodes:
                node_sid, itime = inode.rsplit('-', 1)
                if node_sid == pre:
                    try:
                        itime = int(itime)
                    except ValueError:
                        itime = int(itime.split('~')[0])
                    if (next_step - dfg[pre][sid]['time_shifted'] >= itime
                            >= pre_time):
                        pre_node = inode
                        pre_time = itime
            if pre_node is not None:
                eg.add_edge(pre_node, node_id)
                assert eg.nodes[pre_node]['t'] <= eg.nodes[node_id]['t']

    for suc in dfg.successors(sid):
        if dfg[sid][suc]['async_requests'] and sim.last_step >= 0:
            suc_node = node % (suc, sims[suc].last_step)
            eg.add_edge(suc_node, node_id)
            assert sims[suc].progress + 1 >= next_step


def post_step(world, sim):
    """
    Record time after a step and add self-step edge.
    """
    eg = world.execution_graph
    last_node = sim.last_node
    eg.nodes[last_node]['t_end'] = perf_counter()
    next_self_step = sim.next_self_step
    if next_self_step is not None and next_self_step < world.until:
        node = '%s-%s'
        node_id = node % (sim.sid, next_self_step)
        eg.add_edge(sim.last_node, node_id)
        sim.next_self_step = None
