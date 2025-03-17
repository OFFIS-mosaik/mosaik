# pyright: reportUnknownMemberType=false
"""
This module contains some utility functions and classes.

"""

from __future__ import annotations

import datetime
import random
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Collection,
    Dict,
    Iterable,
    List,
    MutableSequence,
    Optional,
    Set,
    Tuple,
)

import networkx as nx
from mosaik_api_v3 import Attr, SimId
from typing_extensions import Literal

from mosaik.async_scenario import AsyncWorld
from mosaik.scenario import Entity, World
from mosaik.tiered_time import TieredTime

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.figure import Figure

STANDARD_DPI = 600
STANDARD_FORMAT = "png"
STANDARD_FOLDER = "figures"


def connect_many_to_one(
    world: World | AsyncWorld,
    src_set: Iterable[Entity],
    dest: Entity,
    *attrs: Attr | Tuple[Attr, Attr],
    async_requests: bool = False,
    transform: Callable[[Any], Any] = lambda x: x,
):
    """:meth:`~mosaik.scenario.World.connect` each entity in *src_set*
    to *dest*.

    See the :meth:`~mosaik.scenario.World.connect` for more details.
    """
    for src in src_set:
        world.connect(
            src, dest, *attrs, async_requests=async_requests, transform=transform
        )


def connect_randomly(
    world: World | AsyncWorld,
    src_set: MutableSequence[Entity],
    dest_set: MutableSequence[Entity],
    *attrs: Attr | Tuple[Attr, Attr],
    evenly: bool = True,
    max_connects: int = float("inf"),  # type: ignore
):
    """
    Randomly :meth:`~mosaik.scenario.World.connect` the entities from
    ``src_set`` to the entities from ``dest_set`` and return a subset of
    ``dest_set`` containing all entities with a connection.

    :param world: the instance of the :class:`~mosaik.scenario.World`
        to which the entities belong.

    :param src_set: a :class:`~collections.abc.MutableSequence`
        (potentially empty) containing :class:`~mosaik.scenario.Entity`
        instances. Each of these entities will be connected to an entity
        of ``dest_set``.

    :param dest_set: a non-empty
        :class:`~collections.abc.MutableSequence` of
        :class:`~mosaik.scenario.Entity` instances. Not every of these
        entities is necessarily connected (if ``src_set`` contains too
        few entities)

    :params attrs: the attribute names to connect as in
        :meth:`~mosaik.scenario.World.connect()`.

    :param evenly: How to distribute the entities:

        If ``True``, entity connections will be distributed
        as evenly as possible. That means if you connect a set of three
        entities to a set of three entities, there will be three 1:1
        connections; if you connect four entities to three entities,
        there will be one 2:1 and two 1:1 connections.

        If ``False``, connections will be truly random. That means if
        you connect three entities to three entities, you may either
        have three 1:1 connections, one 2:1 and two 1:1 connections
        or just one 3:1 connection.

    :param max_connects: the maximum number of connections that an
        entity of ``dest_set`` may receive. This argument is only taken
        into account if ``evenly`` is set to ``False``.

    :return: The :class:`list` of entities from ``dest_set`` to which
        entities from ``src_set`` were actually connected.
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


def connect_zip(
    world: World | AsyncWorld,
    src_set: Collection[Entity],
    dest_set: Collection[Entity],
    *attrs: Attr | Tuple[Attr, Attr],
    **kwargs,
) -> None:
    """Connect entities in parallel. This works analogously to the
    built-in :func:`zip` function: Each entity in ``src_set`` is
    connected to the entity in ``dest_set`` at the corresponding index.

    :param world: the world for this simulation
    :param src_set: the collection of source entities
    :param dest_set: the collection of destination entities
    :param attrs: the attributes to connect, as in :meth:`world.connect
        <mosaik.async_scenario.AsyncWorld.connect>`
    :param kwargs: the connection kwargs as in :meth:`world.connect
        <mosaik.async_scenario.AsyncWorld.connect>`

    :raise ValueError: if ``src_set`` and ``dest_set`` don't have the
        same number of elements
    """
    for src, dest in zip(src_set, dest_set, strict=True):
        world.connect(src, dest, *attrs, **kwargs)


def _connect_evenly(
    world: World | AsyncWorld,
    src_set: MutableSequence[Entity],
    dest_set: MutableSequence[Entity],
    *attrs: Attr | Tuple[Attr, Attr],
) -> Set[Entity]:
    connect = world.connect
    connected: Set[Entity] = set()

    src_size, dest_size = len(src_set), len(dest_set)
    pos = 0
    while pos < src_size:
        random.shuffle(dest_set)
        for src, dest in zip(src_set[pos:], dest_set):
            connect(src, dest, *attrs)
            connected.add(dest)
        pos += dest_size

    return connected


def _connect_randomly(
    world: World | AsyncWorld,
    src_set: MutableSequence[Entity],
    dest_set: MutableSequence[Entity],
    *attrs: Attr | Tuple[Attr, Attr],
    max_connects: int = float("inf"),  # type: ignore
) -> Set[Entity]:
    connect = world.connect
    connected: Set[Entity] = set()

    assert len(src_set) <= (len(dest_set) * max_connects)
    max_i = len(dest_set) - 1
    randint = random.randint
    connects: Dict[Entity, int] = {}
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
    world: World,
    folder: str = STANDARD_FOLDER,
    hdf5path: str | None = None,
    dpi: int = STANDARD_DPI,
    format: Literal["png", "pdf", "svg"] = STANDARD_FORMAT,
    show_plot: bool = True,
    slice: Tuple[int, int] | None = None,
):
    """Creates an image visualizing the execution time of the different
    simulators of a mosaik scenario.

    :param world: mosaik world object
    :param folder: folder to store the image (only if no hdf5path is
        provided)
    :param hdf5path: Path to HDF5 file, which will be used as path for
        the created image
    :param dpi: DPI for created images
    :param format: format for created image
    :param show_plot: whether to open a window to show the plot
    :param slice: reduce the timeframe that you show in the plot. Usage
        as in Python list slicing, i.e., negative values are possible to
        start from the end of the list. Jumps are not possible.
        ``slice`` needs to be a two-element integer list, e.g.
        ``(0, 5)``.

    :return: ``None`` but image file will be written to file system
    """
    import matplotlib.pyplot as plt

    steps = {}
    all_nodes = list(world.execution_graph.nodes(data=True))

    # Slice the data if the slice reduces the timesteps to be shown
    if slice is not None:
        slices_steps = range(world.until)[slice[0] : slice[1]]
        all_nodes_sliced = []
        for node in all_nodes:
            if node[0][1].time in slices_steps:
                all_nodes_sliced.append(node)
        all_nodes = all_nodes_sliced

    t_min = min([node[1]["t"] for node in all_nodes])
    t_max = max([node[1]["t_end"] for node in all_nodes])

    for isid in world.sims.keys():
        steps[isid] = []
        for node in all_nodes:
            if node[0][0] == isid:
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
    world: World,
    folder: str = STANDARD_FOLDER,
    hdf5path: Optional[str] = None,
    dpi: int = STANDARD_DPI,
    format: Literal["png", "pdf", "svg"] = STANDARD_FORMAT,
    show_plot: bool = True,
):
    """Creates an image visualizing the data flow graph of a mosaik
    scenario. Using the spring layout from Matplotlib (Fruchterman-
    Reingold force-directed algorithm) to position the nodes.

    :param world: mosaik world object
    :param folder: folder to store the image (only if no hdf5path is
        provided)
    :param hdf5path: Path to HDF5 file, which will be used as path for
        the created image
    :param dpi: DPI for created images
    :param format: format for created image
    :param show_plot: whether open a window to show the plot
    :return: ``None`` but image file will be written to file
        system
    """
    import matplotlib.pyplot as plt
    from matplotlib.patches import ConnectionPatch

    # Recreate the df_graph for plotting. There might be additional
    # useful information to be extracted from the SimRunners.
    df_graph: nx.DiGraph[str] = nx.DiGraph()
    for sim in world.sims.values():
        df_graph.add_node(sim.sid)
        for pred, delay in sim.input_delays.items():
            df_graph.add_edge(
                pred.sid,
                sim.sid,
                time_shifted=delay.is_time_shifted(),
                weak=delay.is_weak(),
            )
    positions = nx.spring_layout(df_graph)

    fig, ax = plt.subplots()
    for node in df_graph.nodes:
        # Draw a dot for the simulator
        ax.plot(positions[node][0], positions[node][1], "o")
        # Put the name of the simulator on the dot. If we put an
        # absolute distance, we depend on the scaling, which can effect
        # seemingly random distances from the dot
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

        # Attention: This is not the actual mid-point in the line!
        # I suspect it's more like a control point in a bezier
        # interpolation. When the line is more curved, the middle point
        # here is further away from the actual line. One could suspect
        # that the mid-point is actually the middle point in this array,
        # but the array starts with the stating point, then has the
        # curve-control point in the middle and then has the points that
        # draw the arrow.
        # Why not calculating the middle point on the straight line?
        # Because then by a 50/50 chance when you have a curved arrow
        # back and forth between two points, you can have the annotation
        # above the wrong arrow.
        midpoint: Tuple[float, float] = con.get_path().vertices[1]  # type: ignore  # close enough

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


def plot_execution_graph(  # noqa: C901
    world: World,
    title: str = "",
    folder: str = STANDARD_FOLDER,
    hdf5path: str | None = None,
    dpi: int = STANDARD_DPI,
    format: Literal["png", "pdf", "svg"] = STANDARD_FORMAT,
    show_plot: bool = True,
    save_plot: bool = True,
    slice: Tuple[int, int] | None = None,
):
    """Creates an image visualizing the execution graph of a mosaik
    scenario.

    :param world: mosaik world object
    :param title: the title of the graph
    :param folder: folder to store the image (only if no hdf5path is
        provided)
    :param hdf5path: Path to HDF5 file, which will be used as path for
        the created image
    :param dpi: DPI for created images
    :param format: format for created image
    :param show_plot: whether to open a window to show the plot
    :param slice: reduce the timeframe that you show in the plot.
        Usage as in Python list slicing, i.e., negative values are
        possible to start from the end of the list. Jumps are not
        possible. ``slice`` needs to be a two-element integer tuple,
        e.g. ``(0, 5)``.

    :return: ``None`` but image file will be written to file system
    """
    import matplotlib.pyplot as plt
    from matplotlib import rcParams
    from matplotlib.ticker import MaxNLocator

    all_nodes = list(world.execution_graph.nodes(data=True))

    rcParams.update({"figure.autolayout": True})

    steps_st: Dict[SimId, List[float]] = {}
    for sim_name in world.sims.keys():
        steps_st[sim_name] = []

    for node in all_nodes:
        sim_name, tiered_time = node[0]
        steps_st[sim_name].append(_tiered_time_pos(tiered_time))

    fig, ax = plt.subplots()
    if title:
        fig.suptitle(title)

    # Draw the time steps from the simulators
    number_of_steps = 0
    colormap = ["black" for _ in world.sims]
    for i, sim_name in enumerate(world.sims):
        # We need the number of steps in the simulation for correct
        # plotting with slices
        if number_of_steps < len(steps_st[sim_name]):
            number_of_steps = len(steps_st[sim_name])

        if slice is not None:
            dot = ax.plot(
                steps_st[sim_name][slice[0] : slice[1]],
                [i] * len(steps_st[sim_name][slice[0] : slice[1]]),
                "o",
            )
        else:
            dot = ax.plot(steps_st[sim_name], [i] * len(steps_st[sim_name]), "o")
        # Store the color that is used for the dots in this line
        # (for this simulator)
        colormap[i] = dot[0].get_color()

    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    ax.set_yticks(list(range(len(world.sims.keys()))))
    ax.set_yticklabels(list(world.sims.keys()))

    all_edges = list(world.execution_graph.edges())
    y_pos: Dict[SimId, int] = {}
    for sim_count, sim_name in enumerate(world.sims.keys()):
        y_pos[sim_name] = sim_count

    # The slice values can be negative, so we want to have the correct
    # time steps
    labels = None
    if slice is not None:
        labels = range(world.until)[slice[0] : slice[1]]

    for edge in all_edges:
        isid_0, t0 = edge[0]
        isid_1, t1 = edge[1]

        if arrow_is_not_in_slice(labels, t0.time, t1.time):
            continue

        x_pos0 = _tiered_time_pos(t0)
        x_pos1 = _tiered_time_pos(t1)
        y_pos0 = y_pos[isid_0]
        y_pos1 = y_pos[isid_1]

        ax.annotate(
            "",
            (x_pos1, y_pos1),
            xytext=(x_pos0, y_pos0),
            arrowprops={
                "color": colormap[y_pos0],
                "arrowstyle": "->",
                "connectionstyle": "arc3,rad=0.05",
                "alpha": 0.6,
            },
        )

    if show_plot is True:
        plt.show()

    if hdf5path:
        filename: str = hdf5path.replace(".hdf5", "graph_execution." + format)
    else:
        filename: str = get_filename(folder, "executionGraph", format)

    if save_plot:
        fig.savefig(
            filename,
            format=format,
            dpi=dpi,
            facecolor="white",
            transparent=True,
            bbox_inches="tight",
        )


def arrow_is_not_in_slice(
    labels: Collection[int] | None,
    t0: int,
    t1: int,
):
    return labels is not None and (t0 not in labels or t1 not in labels)


def plot_execution_time_per_simulator(
    world: World,
    folder: str = STANDARD_FOLDER,
    hdf5path: str | None = None,
    dpi: int = STANDARD_DPI,
    format: Literal["png", "pdf", "svg"] = STANDARD_FORMAT,
    show_plot: bool = True,
    plot_per_simulator: bool = False,
    slice: Tuple[int, int] | None = None,
):
    """Creates images visualizing the execution time of each of the
    different simulators of a mosaik scenario.

    :param world: mosaik world object
    :param folder: folder to store the image (only if no hdf5path is
        provided)
    :param hdf5path: Path to HDF5 file, which will be used as path for
        the created image
    :param dpi: DPI for created images
    :param format: format for created image
    :param show_plot: whether to open a window to show the plot
    :param plot_per_simulator: whether to create a separated plot per
        simulator. This is especially useful if the step sizes of the
        simulators are very different.
    :param slice: reduce the timeframe that you show in the plot. Usage
        as in Python list slicing, i.e., negative values are possible to
        start from the end of the list. Jumps are not possible.
        ``slice`` needs to be a two-element integer tuple, e.g.
        ``(0, 5)``.
    :return: ``None`` but image file will be written to file system
    """
    execution_graph = world.execution_graph
    results: Dict[SimId, List[float]] = {}
    for node in execution_graph.nodes:
        execution_time = (
            execution_graph.nodes[node]["t_end"] - execution_graph.nodes[node]["t"]
        )
        sim_id = node[0]
        results.setdefault(sim_id, []).append(execution_time)

    if plot_per_simulator is False:
        fig, sub_figure = init_execution_time_per_simulator_plot()
        for key in results.keys():
            plot_results = get_execution_time_per_simulator_plot_data(
                slice, results, sub_figure, key
            )
            sub_figure.plot(plot_results, label=key)
        finish_execution_time_per_simulator_plot(
            folder, hdf5path, dpi, format, show_plot, fig
        )
    else:
        for key in results.keys():
            fig, sub_figure = init_execution_time_per_simulator_plot()
            plot_results = get_execution_time_per_simulator_plot_data(
                slice, results, sub_figure, key
            )
            sub_figure.plot(plot_results, label=key)
            finish_execution_time_per_simulator_plot(
                folder, hdf5path, dpi, format, show_plot, fig, "_" + key
            )


def get_execution_time_per_simulator_plot_data(
    slice: Tuple[int, int] | None,
    results: Dict[SimId, List[float]],
    sub_figure: Axes,
    key: SimId,
) -> List[float]:
    if slice is not None:
        plot_results = results[key][slice[0] : slice[1]]
        # The slice values can be negative, so we want to have the
        # correct time steps
        labels = range(len(results[key]))[slice[0] : slice[1]]
        sub_figure.set_xticks(range(0, len(labels)), map(str, labels))
    else:
        plot_results = results[key]
    return plot_results


def finish_execution_time_per_simulator_plot(
    folder: str,
    hdf5path: str | None,
    dpi: int,
    format: Literal["png", "svg", "pdf"],
    show_plot: bool,
    fig: Figure,
    simulator_name: str = "",
):
    import matplotlib.pyplot as plt

    fig.legend()
    if hdf5path:
        filename: str = hdf5path.replace(".hdf5", "_" + "all" + ".png")
    else:
        filename: str = get_filename(
            folder, "execution_time_simulator" + simulator_name, format
        )

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


def init_execution_time_per_simulator_plot() -> Tuple[Figure, Axes]:
    import matplotlib.pyplot as plt
    from matplotlib.ticker import MaxNLocator

    fig: Figure = plt.figure()
    sub_figure: Axes = fig.add_subplot()
    sub_figure.set_title("Execution time")
    sub_figure.set_ylabel("Execution time [s]")
    sub_figure.set_xlabel("Simulation time [steps of the simulator]")
    sub_figure.get_xaxis().set_major_locator(MaxNLocator(integer=True))
    return fig, sub_figure


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


def _tiered_time_pos(time: TieredTime, base: float = 0.1) -> float:
    result = 0.0
    factor = 1.0
    for tier in time.tiers:
        result += factor * tier
        factor *= base
    return result


def plot_dataflow(
    world: World,
    file_name: str | None = None,
    dpi: int = STANDARD_DPI,
    format: Literal["png", "pdf", "svg"] = STANDARD_FORMAT,
    show_plot: bool = True,
    return_figure: bool = True,
    seed: int | None = None,
    **kwargs: Any,
) -> None | Tuple[Figure, Axes]:
    """Creates an image visualizing the data flow graph of a mosaik
    scenario. Using the spring layout from Matplotlib (Fruchterman-
    Reingold force-directed algorithm) to position the nodes.

    :param world: mosaik world object
    :param file_name: a full file name including a folder to
        store the image
    :param dpi: DPI for created images
    :param format: format for created image
    :param show_plot: whether open a window to show the plot
    :param return_figure: return figure and axis
    :param seed: needed to fix graph layout
    :param **kwargs: extra parameters will be passed to fig.savefig()
    :return: ``None`` but image file will be written to ``file name``
        if given. It returns tuple with figure and axis instead if
        return_figure is True
    """
    import matplotlib.pyplot as plt
    from matplotlib.patches import ConnectionPatch

    # Recreate the df_graph for plotting. There might be additional
    # useful information to be extracted from the SimRunners.
    df_graph: nx.DiGraph[str] = nx.DiGraph()
    for sim in world.sims.values():
        df_graph.add_node(sim.sid)
        for pred, delay in sim.input_delays.items():
            df_graph.add_edge(
                pred.sid,
                sim.sid,
                time_shifted=delay.is_time_shifted(),
                weak=delay.is_weak(),
            )
    positions = nx.spring_layout(df_graph, seed=seed)

    fig, ax = plt.subplots()

    for node in df_graph.nodes:
        # Draw a dot for the simulator
        ax.plot(positions[node][0], positions[node][1], "o")
        # Put the name of the simulator on the dot. If we put an
        # absolute distance, we depend on the scaling, which can effect
        # seemingly random distances from the dot
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

        midpoint: Tuple[float, float] = con.get_path().vertices[1]

        ax.annotate(
            annotation,
            (midpoint[0], midpoint[1]),
            xytext=(0, 0),
            textcoords="offset points",
            color=color,
            fontsize=5,
        )

    plt.axis("off")

    if file_name:
        kwargs.setdefault("facecolor", "white")
        kwargs.setdefault("edgecolor", "auto")
        kwargs.setdefault("transparent", True)
        kwargs.setdefault("bbox_inches", "tight")
        fig.savefig(
            file_name,
            format=format,
            dpi=dpi,
            **kwargs,
        )

    if show_plot:
        plt.show()

    if return_figure:
        return fig, ax
