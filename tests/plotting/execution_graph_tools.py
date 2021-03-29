import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator


def plot_execution_graph(world):
    steps = {}

    all_nodes = list(world.execution_graph.nodes(data=True))
    t_min = min([node[1]['t'] for node in all_nodes])
    t_max = max([node[1]['t_end'] for node in all_nodes])

    for isid in world.sims.keys():
        steps[isid] = []
        for node in all_nodes:
            if node[0].startswith(isid):
                steps[isid].append((node[1]['t'] - t_min, (node[1]['t_end']-node[1]['t'])))

    fig, ax = plt.subplots()
    for i, isid in enumerate(world.sims.keys()):
        ax.broken_barh(steps[isid], ((i+1)*10, 9), facecolors='tab:blue')
    ax.set_xlim(0, t_max - t_min)
    ax.set_ylim(5, len(world.sims.keys())*10 + 15)
    ax.set_yticks(list(range(15, len(world.sims.keys())*10 + 10, 10)))
    ax.set_yticklabels(list(world.sims.keys()))
    ax.grid(True)
    plt.show()


def split_node(node):
    isid, t = node.rsplit('-', 1)
    try:
        t = int(t)
        n_rep = 0
    except ValueError:
        t, n_rep = map(int, t.split('~'))

    if isid.endswith('-'):
        isid = isid.strip('-')
        t = -1
    return isid, t, n_rep


def plot_execution_graph_st(world, title=''):
    all_nodes = list(world.execution_graph.nodes(data=True))

    steps_st = {}
    for isid in world.sims.keys():
        steps_st[isid] = []

    for node in all_nodes:
        print(node[0])
        isid, t, n_rep = split_node(node[0])
        steps_st[isid].append(t + n_rep*0.1)

    fig, ax = plt.subplots()
    if title:
        fig.suptitle(title)

    for i, isid in enumerate(world.sims.keys()):
        ax.plot(steps_st[isid], [i]*len(steps_st[isid]), 'o')

    ax.xaxis.set_major_locator(MaxNLocator(integer=True))

    ax.set_yticks(list(range(len(world.sims.keys()))))
    ax.set_yticklabels(list(world.sims.keys()))

    all_edges = list(world.execution_graph.edges())
    print(all_edges)

    y_pos = {}
    for ii, isid in enumerate(world.sims.keys()):
        y_pos[isid] = ii

    for edge in all_edges:
        isid_0, t0, n_rep0 = split_node(edge[0])
        isid_1, t1, n_rep1 = split_node(edge[1])
        x_pos0 = t0 + n_rep0 * 0.1
        x_pos1 = t1 + n_rep1 * 0.1
        y_pos0 = y_pos[isid_0]
        y_pos1 = y_pos[isid_1]

        ax.annotate('', (x_pos1, y_pos1), xytext=(x_pos0, y_pos0),
                    arrowprops=dict(facecolor='black', arrowstyle="->"))

    plt.show()
