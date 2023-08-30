"""
This module contains some utility functions and classes.

"""
import random
import networkx as nx
import datetime


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
    show_plot=True,
    slice=None,
):
    """
        Creates an image visualizing the execution time of the different simulators of a mosaik scenario.

    :param world: mosaik world object
    :param folder: folder to store the image (only if no hdf5path is provided)
    :param hdf5path: Path to HDF5 file, which will be used as path for the created image
    :param dpi: DPI for created images
    :param format: format for created image
    :show_plot: open a window to show the plot
    :param slice: reduce the timeframe that you show in the plot. Usage as python list slicing,
    i.e., negative values are possible to start from the end of the list. Jumps are not possible.
    Slice needs to be a two-parameter integer list, e.g. [0,5].
    :return: no return object, but image file will be written to file system
    """
    import matplotlib.pyplot as plt

    steps = {}
    all_nodes = list(world.execution_graph.nodes(data=True))

    # Slice the data if the slice reduces the timesteps to be shown
    if slice is not None:
        slices_steps = range(world.until)[slice[0] : slice[1]]
        all_nodes_sliced = []
        for node in all_nodes:
            if int(node[0].split("-")[-1]) in slices_steps:
                all_nodes_sliced.append(node)
        all_nodes = all_nodes_sliced

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
    if show_plot is True:
        plt.show()


def plot_dataflow_graph(
    world,
    folder=STANDARD_FOLDER,
    hdf5path=None,
    dpi=STANDARD_DPI,
    format=STANDARD_FORMAT,
    show_plot=True,
):
    """
    Creates an image visualizing the data flow graph of a mosaik scenario. Using the spring_layout from
    Matplotlib (Fruchterman-Reingold force-directed algorithm) to position the nodes.

    :param world: mosaik world object
    :param folder: folder to store the image (only if no hdf5path is provided)
    :param hdf5path: Path to HDF5 file, which will be used as path for the created image
    :param dpi: DPI for created images
    :param format: format for created image
    :show_plot: open a window to show the plot
    :return: no return object, but image file will be written to file system
    """
    import matplotlib.pyplot as plt
    from matplotlib.patches import ConnectionPatch

    df_graph = world.df_graph
    positions = nx.spring_layout(df_graph)
    fig, ax = plt.subplots()
    for node in df_graph.nodes:
        # Draw a dot for the simulator
        ax.plot(positions[node][0], positions[node][1], "o")
        # Put the name of the simulator on the dot. If we put an absolute distance, we depend on the scaling, which
        # can effect seemingly random distances from the dot
        text_x = positions[node][0]
        text_y = positions[node][1]
        label = ax.annotate(node, positions[node], xytext=(text_x, text_y), size=4)
        label.set_alpha(0.6)

    for edge in list(df_graph.edges()):
        edge_infos = df_graph.adj[edge[0]][edge[1]]
        annotation = ""
        color = "grey"
        linestyle = "solid"
        if edge_infos["time_shifted"]:
            color = "tab:red"
            annotation = "time_shifted"

        if edge_infos["weak"]:
            annotation += " weak"
            linestyle = "dotted"

        x_pos0 = positions[edge[0]][0]
        x_pos1 = positions[edge[1]][0]
        y_pos0 = positions[edge[0]][1]
        y_pos1 = positions[edge[1]][1]

        con = ConnectionPatch(
            (x_pos0, y_pos0),
            (x_pos1, y_pos1),
            "data",
            "data",
            arrowstyle="->",
            linestyle=linestyle,
            connectionstyle="arc3,rad=0.1",
            shrinkA=5,
            shrinkB=5,
            mutation_scale=20,
            fc="w",
            color=color,
            alpha=0.6,
        )
        ax.add_artist(con)

        # Attention: This is not the actual mid-point in the line
        # I suspect its more like a control point in a bezier interpolation
        # When the line is more curved, the middle point here is further away from the actual line
        # One could suspect that the mid-point is actually the middle point in this array,
        # but the array starts with the stating point, then has the curve-control point in the middle
        # and then has the points that draw the arrow
        # Why not calculating the middle point on the straight line? Because then by a 50/50 chance
        # when you have a curved arrow back and forth between two points, you can have the annotation
        # above the wrong arrow.
        midpoint = con.get_path().vertices[1]

        ax.annotate(
            annotation,
            (midpoint[0], midpoint[1]),
            xytext=(0, 0),
            textcoords="offset points",
            color=color,
            fontsize=5,
        )

    plt.axis("off")

    if show_plot is True:
        plt.show()

    if hdf5path:
        filename: str = hdf5path.replace(".hdf5", "graph_df." + format)
    else:
        filename: str = get_filename(folder, "dataflowGraph_2", format)

    fig.savefig(
        filename,
        format=format,
        dpi=dpi,
        facecolor="white",
        transparent=True,
        bbox_inches="tight",
    )


def plot_execution_graph(
    world,
    title="",
    folder=STANDARD_FOLDER,
    hdf5path=None,
    dpi=STANDARD_DPI,
    format=STANDARD_FORMAT,
    show_plot=True,
    slice=None,
):
    """
        Creates an image visualizing the execution graph of a mosaik scenario.

    :param world: mosaik world object
    :param title:
    :param folder: folder to store the image (only if no hdf5path is provided)
    :param hdf5path: Path to HDF5 file, which will be used as path for the created image
    :param dpi: DPI for created images
    :param format: format for created image
    :show_plot: open a window to show the plot
    :param slice: reduce the timeframe that you show in the plot. Usage as python list slicing,
    i.e., negative values are possible to start from the end of the list. Jumps are not possible.
    Slice needs to be a two-parameter integer list, e.g. [0,5].
    :return: no return object, but image file will be written to file system
    """
    import matplotlib.pyplot as plt
    from matplotlib import rcParams
    from matplotlib.ticker import MaxNLocator

    all_nodes = list(world.execution_graph.nodes(data=True))

    rcParams.update({"figure.autolayout": True})

    steps_st = {}
    for sim_name in world.sims.keys():
        steps_st[sim_name] = []

    for node in all_nodes:
        sim_name, t, n_rep = split_node(node[0])
        steps_st[sim_name].append(t + n_rep * 0.1)

    fig, ax = plt.subplots()
    if title:
        fig.suptitle(title)

    # Draw the time steps from the simulators
    number_of_steps = 0
    colormap = ["black" for x in range(len(world.sims.keys()))]
    for i, sim_name in enumerate(world.sims.keys()):
        # We need the number of steps in the simulation for correct plotting with slices
        if number_of_steps < len(steps_st[sim_name]):
            number_of_steps = len(steps_st[sim_name])

        if slice != None:
            dot = ax.plot(
                steps_st[sim_name][slice[0] : slice[1]],
                [i] * len(steps_st[sim_name][slice[0] : slice[1]]),
                "o",
            )
        else:
            dot = ax.plot(steps_st[sim_name], [i] * len(steps_st[sim_name]), "o")
        # Store the color that is used for the dots in this line (for this simulator)
        colormap[i] = dot[0].get_color()

    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    ax.set_yticks(list(range(len(world.sims.keys()))))
    ax.set_yticklabels(list(world.sims.keys()))

    all_edges = list(world.execution_graph.edges())
    y_pos = {}
    for sim_count, sim_name in enumerate(world.sims.keys()):
        y_pos[sim_name] = sim_count

    # The slice values can be negative, so we want to have the correct time steps
    labels = None
    if slice is not None:
        labels = range(world.until)[slice[0] : slice[1]]

    for edge in all_edges:
        isid_0, t0, n_rep0 = split_node(edge[0])
        isid_1, t1, n_rep1 = split_node(edge[1])

        if arrow_is_not_in_slice(labels, t0, t1):
            continue

        x_pos0 = t0 + n_rep0 * 0.1
        x_pos1 = t1 + n_rep1 * 0.1
        y_pos0 = y_pos[isid_0]
        y_pos1 = y_pos[isid_1]

        ax.annotate(
            "",
            (x_pos1, y_pos1),
            xytext=(x_pos0, y_pos0),
            arrowprops=dict(
                color=colormap[y_pos0],
                arrowstyle="->",
                connectionstyle="arc3,rad=0.05",
                alpha=0.6,
            ),
        )
    
    if show_plot is True:
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


def arrow_is_not_in_slice(labels, t0, t1):
    return labels is not None and (t0 not in labels or t1 not in labels)


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


def plot_execution_time_per_simulator(
    world,
    folder=STANDARD_FOLDER,
    hdf5path=None,
    dpi=STANDARD_DPI,
    format=STANDARD_FORMAT,
    show_plot=True,
    slice=None,
):
    """
        Creates images visualizing the execution time of each of the different simulators of a mosaik scenario.

    :param world: mosaik world object
    :param folder: folder to store the image (only if no hdf5path is provided)
    :param hdf5path: Path to HDF5 file, which will be used as path for the created image
    :param dpi: DPI for created images
    :param format: format for created image
    :show_plot: open a window to show the plot
    :param slice: reduce the timeframe that you show in the plot. Usage as python list slicing,
    i.e., negative values are possible to start from the end of the list. Jumps are not possible.
    Slice needs to be a two-parameter integer list, e.g. [0,5].
    :return: no return object, but image file will be written to file system
    """
    import matplotlib.pyplot as plt
    from matplotlib.ticker import MaxNLocator

    execution_graph = world.execution_graph
    results = {}
    for node in execution_graph.nodes:
        execution_time = (
            execution_graph.nodes[node]["t_end"] - execution_graph.nodes[node]["t"]
        )
        sim_id = node.split("-")[0] + "-" + node.split("-")[1]
        if sim_id not in results:
            results[sim_id] = []
        results[sim_id].append(execution_time)

    fig = plt.figure()
    sub_figure = fig.add_subplot()
    sub_figure.set_title("Execution time")
    sub_figure.set_ylabel("Execution time [s]")
    sub_figure.set_xlabel("Simulation time [steps of the simulator]")
    sub_figure.get_xaxis().set_major_locator(MaxNLocator(integer=True))
    for key in results.keys():
        if slice is not None:
            plot_results = results[key][slice[0] : slice[1]]
            # The slice values can be negative, so we want to have the correct time steps
            labels = range(len(results[key]))[slice[0] : slice[1]]
            sub_figure.set_xticks(range(0, len(labels)), labels)
        else:
            plot_results = results[key]
        sub_figure.plot(plot_results, label=key)
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
    
    if show_plot is True:
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
