"""
This module contains some utility functions and classes.

"""
import random
import matplotlib.pyplot as plt
import networkx as nx
import datetime
import matplotlib.colors as mcolors
from matplotlib.ticker import MaxNLocator


STANDARD_DPI = 600
STANDARD_FORMAT = "png"
STANDARD_FOLDER = "figures"


def connect_many_to_one(world, src_set, dest, *attrs, async_requests=False):
    """
    :meth:`~mosaik.scenario.World.connect` each entity in *src_set*
    to *dest*.

    See the :meth:`~mosaik.scenario.World.connect` for more details.
    """
    for src in src_set:
        world.connect(src, dest, *attrs, async_requests=async_requests)


def connect_randomly(
    world, src_set, dest_set, *attrs, evenly=True, max_connects=float("inf")
):
    """
    Randomly :meth:`~mosaik.scenario.World.connect` the entities from
    *src_set* to the entities from *dest_set* and return a subset of *dest_set*
    containing all entities with a connection.

    *world* is an instance of the :class:`~mosaik.scenario.World` to which the
    entities belong.

    *src_set* and *dest_set* are iterables containing
    :class:`~mosaik.scenario.Entity` instances. *src_set* may be empty,
    *dest_set* must not be empty. Each entity of *src_set* will be connected to
    an entity of *dest_set*, but not every entity of *dest_set* will
    necessarily have a connection (e.g., if you connect a set of three entities
    to a set of four entities). A set of all entities from *dest_set*, to which
    at least one entity from *src_set* was connected, will be returned.

    *attrs* is a list of attribute names of pairs as in
    :meth:`~mosaik.scenario.World.connect()`.

    If the flag *evenly* is set to ``True``, entities connections will be
    distributed as evenly as possible. That means if you connect a set of three
    entities to a set of three entities, there will be three 1:1 connections;
    if you connect four entities to three entities, there will be one 2:1 and
    two 1:1 connections. If *evenly* is set to ``False``, connections will be
    truly random. That means if you connect three entities to three entities,
    you may either have three 1:1 connections, one 2:1 and two 1:1 connections
    or just one 3:1 connection.

    *max_connects* lets you set the maximum number of connections that an
    entity of *dest_set* may receive. This argument is only taken into account
    if *evenly* is set to ``False``.
    """
    dest_set = list(dest_set)
    assert dest_set

    if evenly:
        connected = _connect_evenly(world, src_set, dest_set, *attrs)
    else:
        connected = _connect_randomly(
            world, src_set, dest_set, *attrs, max_connects=max_connects
        )

    return connected


def _connect_evenly(world, src_set, dest_set, *attrs):
    connect = world.connect
    connected = set()

    src_size, dest_size = len(src_set), len(dest_set)
    pos = 0
    while pos < src_size:
        random.shuffle(dest_set)
        for src, dest in zip(src_set[pos:], dest_set):
            connect(src, dest, *attrs)
            connected.add(dest)
        pos += dest_size

    return connected


def _connect_randomly(world, src_set, dest_set, *attrs, max_connects=float("inf")):
    connect = world.connect
    connected = set()

    assert len(src_set) <= (len(dest_set) * max_connects)
    max_i = len(dest_set) - 1
    randint = random.randint
    connects = {}
    for src in src_set:
        i = randint(0, max_i)
        dest = dest_set[i]
        connect(src, dest, *attrs)
        connected.add(dest)
        connects[dest] = connects.get(dest, 0) + 1
        if connects[dest] >= max_connects:
            dest_set.remove(dest)
            max_i -= 1
            assert max_i >= 0

    return connected


def plot_execution_time(
    world,
    folder=STANDARD_FOLDER,
    hdf5path=None,
    dpi=STANDARD_DPI,
    format=STANDARD_FORMAT,
):
    """
        Creates an image visualizing the execution time of the different simulators of a mosaik scenario.

    :param world: mosaik world object
    :param folder: folder to store the image (only if no hdf5path is provided)
    :param hdf5path: Path to HDF5 file, which will be used as path for the created image
    :param dpi: DPI for created images
    :param format: format for created image
    :return: no return object, but image file will be written to file system
    """
    steps = {}

    all_nodes = list(world.execution_graph.nodes(data=True))
    t_min = min([node[1]["t"] for node in all_nodes])
    t_max = max([node[1]["t_end"] for node in all_nodes])

    for isid in world.sims.keys():
        steps[isid] = []
        for node in all_nodes:
            if node[0].startswith(isid):
                steps[isid].append(
                    (node[1]["t"] - t_min, (node[1]["t_end"] - node[1]["t"]))
                )

    fig, ax = plt.subplots()
    for i, isid in enumerate(world.sims.keys()):
        ax.broken_barh(steps[isid], ((i + 1) * 10, 9), facecolors="tab:blue")
    ax.set_xlim(0, t_max - t_min)
    ax.set_ylim(5, len(world.sims.keys()) * 10 + 15)
    ax.set_yticks(list(range(15, len(world.sims.keys()) * 10 + 10, 10)))
    ax.set_yticklabels(list(world.sims.keys()))
    ax.set_xlabel("Simulation time [s]")
    ax.grid(True)
    if hdf5path:
        filename = hdf5path.replace(".hdf5", "_graph." + format)
    else:
        filename: str = get_filename(folder, "executiontime", format)

    fig.savefig(
        filename,
        format=format,
        dpi=dpi,
        facecolor="white",
        transparent=True,
        bbox_inches="tight",
    )
    plt.show()


def plot_df_graph(
    world,
    folder=STANDARD_FOLDER,
    hdf5path=None,
    dpi=STANDARD_DPI,
    format=STANDARD_FORMAT,
):
    """
        Creates an image visualizing the data flow graph of a mosaik scenario.

    :param world: mosaik world object
    :param folder: folder to store the image (only if no hdf5path is provided)
    :param hdf5path: Path to HDF5 file, which will be used as path for the created image
    :param dpi: DPI for created images
    :param format: format for created image
    :return: no return object, but image file will be written to file system
    """
    df = world.df_graph

    edges_time_shifted = []
    edges_not_time_shifted = []
    for edge in list(df.edges()):
        edge_infos = df.adj[edge[0]][edge[1]]
        if not edge_infos["time_shifted"]:
            edges_not_time_shifted.append(edge)
        else:
            edges_time_shifted.append(edge)

    fig, ax = plt.subplots()

    # Replaced nx.draw_circular with nx.draw_networkx
    # https://stackoverflow.com/questions/74189581/axesstack-object-is-not-callable-while-using-networkx-to-plot
    nx.draw_networkx(df, edgelist=[], with_labels=True, font_size=6, alpha=0.75)
    plt.draw()
    nx.draw_networkx(
        df,
        nodelist=[],
        edgelist=edges_time_shifted,
        arrows=True,
        edge_color="red",
        arrowstyle="->",
        connectionstyle="arc3,rad=0.2",
        alpha=0.5,
    )
    plt.draw()
    nx.draw_networkx(
        df,
        nodelist=[],
        edgelist=edges_not_time_shifted,
        arrows=True,
        arrowstyle="->",
        connectionstyle="arc3,rad=0.2",
        alpha=0.5,
    )
    plt.draw()
    plt.show()
    if hdf5path:
        filename = hdf5path.replace(".hdf5", "graph_df_nx." + format)
    else:
        filename: str = get_filename(folder, "dataflowGraph", format)

    fig.savefig(
        filename,
        format=format,
        dpi=600,
        facecolor="white",
        transparent=True,
        bbox_inches="tight",
    )

    plot_df_graph_via_force_atlas(folder, hdf5path, dpi, format, df)

def plot_df_graph_via_force_atlas(folder: str, hdf5path: str, dpi, format, df):
    try:
        from fa2 import ForceAtlas2
    except ImportError:
        print(
            "ForceAtlas2 could not be imported and execution graph can not be visualized using ForceAtlas algorithm."
        )
        return

    forceatlas2 = ForceAtlas2(
        # Behavior alternatives
        outboundAttractionDistribution=True,  # Dissuade hubs
        linLogMode=False,  # NOT IMPLEMENTED
        adjustSizes=False,  # Prevent overlap (NOT IMPLEMENTED)
        edgeWeightInfluence=1.0,
        # Performance
        jitterTolerance=1.0,  # Tolerance
        barnesHutOptimize=True,
        barnesHutTheta=1.2,
        multiThreaded=False,  # NOT IMPLEMENTED
        # Tuning
        scalingRatio=2.0,
        strongGravityMode=False,
        gravity=10,
        # Log
        verbose=True,
    )

    positions = forceatlas2.forceatlas2_networkx_layout(df, pos=None, iterations=5000)

    fig, ax = plt.subplots()
    for node in df.nodes:
        ax.plot(positions[node][0], positions[node][1], "o")
        text_x = positions[node][0] + 0.5
        text_y = positions[node][1] + 0.5
        label = ax.annotate(node, positions[node], xytext=(text_x, text_y), size=4)
        label.set_alpha = 0.5

    for edge in list(df.edges()):
        edge_infos = df.adj[edge[0]][edge[1]]
        # print(edge_infos['time_shifted'])
        color = "tab:red"
        if not edge_infos["time_shifted"]:
            color = "grey"
        x_pos0 = positions[edge[0]][0]
        x_pos1 = positions[edge[1]][0]
        y_pos0 = positions[edge[0]][1]
        y_pos1 = positions[edge[1]][1]
        ax.annotate(
            "",
            (x_pos1, y_pos1),
            xytext=(x_pos0, y_pos0),
            arrowprops=dict(
                color=color, arrowstyle="->", connectionstyle="arc3,rad=0.2", alpha=0.6
            ),
        )

    # print('Cycles: %s ' % list(nx.simple_cycles(world.execution_graph)))

    plt.axis("off")
    plt.show()
    if hdf5path:
        filename: str = hdf5path.replace(".hdf5", "graph_df." + format)
    else:
        filename: str = get_filename(folder, "dataflowGraph_fa2", format)

    fig.savefig(
        filename,
        format=format,
        dpi=dpi,
        facecolor="white",
        transparent=True,
        bbox_inches="tight",
    )


def split_node(node):
    """

    :param node:
    :return:
    """
    isid, t = node.rsplit("-", 1)
    try:
        t = int(t)
        n_rep = 0
    except ValueError:
        t, n_rep = map(int, t.split("~"))

    if isid.endswith("-"):
        isid = isid.strip("-")
        t = -1
    return isid, t, n_rep


def plot_execution_graph(
    world,
    title="",
    folder=STANDARD_FOLDER,
    hdf5path=None,
    dpi=STANDARD_DPI,
    format=STANDARD_FORMAT,
):
    """
        Creates an image visualizing the execution graph of a mosaik scenario.

    :param world: mosaik world object
    :param title:
    :param folder: folder to store the image (only if no hdf5path is provided)
    :param hdf5path: Path to HDF5 file, which will be used as path for the created image
    :param dpi: DPI for created images
    :param format: format for created image
    :return: no return object, but image file will be written to file system
    """
    all_nodes = list(world.execution_graph.nodes(data=True))

    from matplotlib import rcParams

    rcParams.update({"figure.autolayout": True})

    steps_st = {}
    for isid in world.sims.keys():
        steps_st[isid] = []

    for node in all_nodes:
        # print(node[0])
        isid, t, n_rep = split_node(node[0])
        steps_st[isid].append(t + n_rep * 0.1)

    fig, ax = plt.subplots()
    if title:
        fig.suptitle(title)

    for i, isid in enumerate(world.sims.keys()):
        ax.plot(steps_st[isid], [i] * len(steps_st[isid]), "o")

    ax.xaxis.set_major_locator(MaxNLocator(integer=True))

    ax.set_yticks(list(range(len(world.sims.keys()))))
    ax.set_yticklabels(list(world.sims.keys()))

    all_edges = list(world.execution_graph.edges())
    # print(all_edges)

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

        ax.annotate(
            "",
            (x_pos1, y_pos1),
            xytext=(x_pos0, y_pos0),
            arrowprops=dict(facecolor="black", arrowstyle="->"),
        )

    plt.show()
    if hdf5path:
        filename: str = hdf5path.replace(".hdf5", "graph_execution." + format)
    else:
        filename: str = get_filename(folder, "executionGraph", format)

    fig.savefig(
        filename,
        format=format,
        dpi=dpi,
        facecolor="white",
        transparent=True,
        bbox_inches="tight",
    )


def plot_execution_time_per_simulator(
    world,
    folder=STANDARD_FOLDER,
    hdf5path=None,
    dpi=STANDARD_DPI,
    format=STANDARD_FORMAT,
):
    """
        Creates images visualizing the execution time of each of the different simulators of a mosaik scenario.

    :param world: mosaik world object
    :param folder: folder to store the image (only if no hdf5path is provided)
    :param hdf5path: Path to HDF5 file, which will be used as path for the created image
    :param dpi: DPI for created images
    :param format: format for created image
    :return: no return object, but image file will be written to file system
    """
    eg = world.execution_graph
    results = {}
    for node in eg.nodes:
        execution_time = eg.nodes[node]["t_end"] - eg.nodes[node]["t"]
        sim_id = node.split("-")[0] + "-" + node.split("-")[1]
        if not sim_id in results:
            results[sim_id] = []
        results[sim_id].append(execution_time)

    fig = plt.figure()
    sub_figure = fig.add_subplot()
    sub_figure.set_title("Execution time")
    sub_figure.set_ylabel("Execution time [s]")
    sub_figure.set_xlabel("Simulation time [steps of the simulator]")
    sub_figure.get_xaxis().set_major_locator(MaxNLocator(integer=True))
    for key in results.keys():
        sub_figure.plot(results[key], label=key)
    fig.legend()

    if hdf5path:
        filename: str = hdf5path.replace(".hdf5", "_" + "all" + ".png")
    else:
        filename: str = get_filename(folder, "execution_time_simulator", format)

    fig.savefig(
        filename,
        format=format,
        dpi=dpi,
        facecolor="white",
        transparent=True,
        bbox_inches="tight",
    )
    plt.show()
    plt.close()


def get_filename(dir: str, type: str, file_format: str) -> str:
    return (
        dir
        + "/"
        + str(datetime.datetime.now())
        .replace(" ", "")
        .replace(":", "")
        .replace(".", "")
        + "_"
        + type
        + "."
        + file_format
    )
