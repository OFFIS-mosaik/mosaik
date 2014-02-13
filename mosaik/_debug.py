from time import perf_counter

import mosaik.simulator as sim


_origs = {
    'step': sim.step,
}


def enable(capture_dataflows=False):
    # TODO: optionally capture dataflows
    def wrapped_step(env, sim, inputs):
        pre_step(env, sim)
        return _origs['step'](env, sim, inputs)

    sim.step = wrapped_step


def disable():
    for k, v in _origs.items():
        setattr(sim, k, v)


def pre_step(env, sim):
    eg = env.execution_graph
    sims = env.sims

    sid = sim.sid
    next_step = sim.next_step
    node = '%s-%s'
    node_id = node % (sid, next_step)

    eg.add_node(node_id, t=perf_counter(), st=env.simpy_env.now)
    if sim.last_step >= 0:
        eg.add_edge(node % (sid, sim.last_step), node_id)

    for pre in env.df_graph.predecessors_iter(sid):
        pre_node = node % (pre, sims[pre].last_step)
        eg.add_edge(pre_node, node_id)
        assert eg.node[pre_node]['t'] <= eg.node[node_id]['t']

    for suc in env.df_graph.successors_iter(sid):
        suc_id = node % (suc, sims[suc].next_step)
        assert sims[suc].next_step >= next_step
        assert suc_id not in eg
