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

    def wrapped_step(world, sim, inputs):
        pre_step(world, sim, inputs)
        ret = yield from _originals['step'](world, sim, inputs)
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
    sims = world.sims

    sid = sim.sid
    next_step = sim.next_step
    node = '%s-%s'
    node_id = node % (sid, next_step)

    eg.add_node(node_id, t=perf_counter(), inputs=inputs)

    if sim.last_step >= 0 and next_step == sim.next_self_step:
        eg.add_edge(node % (sid, sim.last_step), node_id)

    for ig, graph in enumerate([world.df_graph, world.shifted_graph]):
        for pre in graph.predecessors(sid):
            messageflows = world.df_graph[pre][sid].get('messageflows', [])
            new_messages = False
            for src_eid, dest_eid, messages in messageflows:
                for src_msg, dest_msg in messages:
                    new_messages = '.'.join(map(str, (pre, src_eid, src_msg))) in inputs.get(dest_eid, {}).get(dest_msg, {}).keys()
                    if new_messages:
                        break
            if not (world.df_graph[pre][sid]['dataflows'] or world.df_graph[pre][sid]['async_requests'] or new_messages):
                break
            if next_step == 0 and (ig == 1 or world.df_graph[pre][sid]['weak']):
                break
            for inode in world.execution_graph.nodes:
                if inode.rsplit('-', 1)[0] == pre:
                    istep = int(inode.rsplit('-', 1)[1])
                    if istep <= next_step - ig:
                        pre_step = istep
                    else:
                        break
            pre_node = node % (pre, pre_step)
            eg.add_edge(pre_node, node_id)

            assert eg.nodes[pre_node]['t'] <= eg.nodes[node_id]['t']

    for suc in world.df_graph.successors(sid):
        if world.df_graph[sid][suc]['async_requests'] and sim.last_step >= 0:
            suc_node = node % (suc, sims[suc].last_step)
            eg.add_edge(suc_node, node_id)
            assert sims[suc].progress >= next_step


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
