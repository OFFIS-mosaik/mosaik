# pyright: reportUnknownMemberType=false
"""
This module contains some utility functions and classes.

"""

from __future__ import annotations

import datetime
import random
from itertools import count, cycle
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

from loguru import logger
from mosaik_api_v3 import Attr, SimId
from typing_extensions import Literal

from mosaik.async_scenario import AsyncWorld
from mosaik.scenario import Entity, World
from mosaik.tiered_time import TieredTime

if TYPE_CHECKING:
    import networkx as nx
    import plotly.graph_objects as go
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

    sims = world._get_sim_runners()
    for isid in sims.keys():
        steps[isid] = []
        for node in all_nodes:
            if node[0][0] == isid:
                steps[isid].append(
                    (node[1]["t"] - t_min, (node[1]["t_end"] - node[1]["t"]))
                )

    fig, ax = plt.subplots()
    for i, isid in enumerate(sims.keys()):
        ax.broken_barh(steps[isid], ((i + 1) * 10, 9), facecolors="tab:blue")
    ax.set_xlim(0, t_max - t_min)
    ax.set_ylim(5, len(sims.keys()) * 10 + 15)
    ax.set_yticks(list(range(15, len(sims.keys()) * 10 + 10, 10)))
    ax.set_yticklabels(list(sims.keys()))
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
    for sim in world._get_sim_runners().values():
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


def quadratic_bezier(
    p0: Tuple[float, float],
    p1: Tuple[float, float],
    p2: Tuple[float, float],
    num: int = 20,
):
    """Return the curve points for a quadratic Bézier segment."""
    if num <= 1:
        return [p0[0]], [p0[1]]

    step = 1.0 / (num - 1)
    ts = [i * step for i in range(num)]
    curve_x: List[float] = []
    curve_y: List[float] = []
    for t in ts:
        one_minus_t = 1 - t
        x = (
            one_minus_t * one_minus_t * p0[0]
            + 2 * one_minus_t * t * p1[0]
            + t * t * p2[0]
        )
        y = (
            one_minus_t * one_minus_t * p0[1]
            + 2 * one_minus_t * t * p1[1]
            + t * t * p2[1]
        )
        curve_x.append(x)
        curve_y.append(y)
    return curve_x, curve_y


def _build_dataflow_graph(world: World | AsyncWorld) -> nx.DiGraph[str]:
    import networkx as nx

    graph: nx.DiGraph[str] = nx.DiGraph()
    for sim in world.sims.values():
        graph.add_node(sim.sid)
        for pred, delay in sim.input_delays.items():
            graph.add_edge(
                pred.sid,
                sim.sid,
                time_shifted=delay.is_time_shifted(),
                weak=delay.is_weak(),
            )
    return graph


def _edge_traces(
    graph: nx.DiGraph[str], pos: Dict[str, Tuple[float, float]]
) -> Tuple[List[go.Scatter], List[dict[str, Any]]]:
    import plotly.graph_objects as go

    traces: List[go.Scatter] = []
    annotations: List[dict[str, Any]] = []
    for src, dst, data in graph.edges(data=True):
        x0, y0 = pos[src]
        x1, y1 = pos[dst]
        control_x = (x0 + x1) / 2 + 0.1 * (y1 - y0)
        control_y = (y0 + y1) / 2 - 0.1 * (x1 - x0)
        curve_x, curve_y = quadratic_bezier(
            (x0, y0),
            (control_x, control_y),
            (x1, y1),
        )

        edge_color = "red" if data.get("time_shifted") else "gray"
        line_style = "dot" if data.get("weak") else "solid"
        labels: List[str] = []
        if data.get("time_shifted"):
            labels.append("Time-Shifted")
        if data.get("weak"):
            labels.append("Weak")
        details = " | ".join(labels) if labels else "Standard Connection"
        hover_text = f"Source: {src}<br>Target: {dst}<br>{details}"

        traces.append(
            go.Scatter(
                x=curve_x,
                y=curve_y,
                line={"width": 1.5, "color": edge_color, "dash": line_style},
                mode="lines",
                hoverinfo="text",
                text=hover_text,
            )
        )

        annotations.append(
            {
                "x": curve_x[-1],
                "y": curve_y[-1],
                "ax": curve_x[-2],
                "ay": curve_y[-2],
                "xref": "x",
                "yref": "y",
                "axref": "x",
                "ayref": "y",
                "showarrow": True,
                "arrowhead": 3,
                "arrowsize": 1.5,
                "arrowwidth": 1.5,
                "arrowcolor": edge_color,
            }
        )
    return traces, annotations


def _node_trace(pos: Dict[str, Tuple[float, float]]) -> go.Scatter:
    import plotly.graph_objects as go

    node_x: List[float] = []
    node_y: List[float] = []
    node_labels: List[str] = []
    for node, (x, y) in pos.items():
        node_x.append(x)
        node_y.append(y)
        node_labels.append(node)

    return go.Scatter(
        x=node_x,
        y=node_y,
        mode="markers+text",
        text=node_labels,
        textposition="top center",
        marker={
            "size": 10,
            "color": "blue",
            "line": {"width": 2, "color": "black"},
        },
    )


def _collect_group_infos(world: World | AsyncWorld) -> Dict[int, Dict[str, Any]]:
    infos: Dict[int, Dict[str, Any]] = {}
    order_counter = count()
    for sim in world.sims.values():
        group = getattr(sim, "group", None)
        current = group
        while current is not None:
            group_id = id(current)
            if group_id not in infos:
                parent_id = id(current.parent) if current.parent else None
                infos[group_id] = {
                    "group": current,
                    "nodes": set(),
                    "parent": parent_id,
                    "order": next(order_counter),
                }
            infos[group_id]["nodes"].add(sim.sid)
            current = current.parent
    return infos


def _rgb_components(color: str) -> Tuple[int, int, int]:
    from plotly.colors import hex_to_rgb

    if color.startswith("#"):
        r, g, b = hex_to_rgb(color)
        return r, g, b
    if color.startswith("rgb"):
        comps = color[color.find("(") + 1 : color.find(")")]
        r, g, b = (int(part.strip()) for part in comps.split(","))
        return r, g, b
    return hex_to_rgb("#1f77b4")  # Fallback color


def _group_label(group_info: Dict[str, Any]) -> str:
    names: List[str] = []
    group_cursor = group_info["group"]
    while group_cursor:
        if group_cursor.name and group_cursor.name != "main":
            names.append(group_cursor.name)
        group_cursor = group_cursor.parent
    if names:
        return " / ".join(reversed(names))
    return f"Group {group_info['order'] + 1}"


def _group_bounds(
    info: Dict[str, Any], pos: Dict[str, Tuple[float, float]], *, margin: float = 0.2
) -> Tuple[float, float, float, float] | None:
    coords = [pos[node_id] for node_id in info["nodes"] if node_id in pos]
    if not coords:
        return None
    xs, ys = zip(*coords)
    min_x = min(xs) - margin
    max_x = max(xs) + margin
    min_y = min(ys) - margin
    max_y = max(ys) + margin
    return min_x, max_x, min_y, max_y


def _group_shapes(
    world: World | AsyncWorld, pos: Dict[str, Tuple[float, float]]
) -> Tuple[List[dict[str, Any]], List[dict[str, Any]]]:
    from plotly.colors import qualitative

    group_infos = _collect_group_infos(world)
    color_cycle = cycle(qualitative.Plotly)
    shapes: List[dict[str, Any]] = []
    labels: List[dict[str, Any]] = []
    for info in sorted(
        group_infos.values(), key=lambda item: (item["group"].depth, item["order"])
    ):
        if info["parent"] is None:
            continue
        bounds = _group_bounds(info, pos)
        if bounds is None:
            logger.info(f"Skipping plotting group {info['group'].name} as it is empty.")
            continue
        min_x, max_x, min_y, max_y = bounds
        color = next(color_cycle)
        r, g, b = _rgb_components(color)
        fill_color = f"rgba({r}, {g}, {b}, 0.08)"
        line_color = f"rgba({r}, {g}, {b}, 0.6)"

        shapes.append(
            {
                "type": "rect",
                "xref": "x",
                "yref": "y",
                "x0": min_x,
                "x1": max_x,
                "y0": min_y,
                "y1": max_y,
                "line": {"color": line_color, "width": 2},
                "fillcolor": fill_color,
                "layer": "below",
            }
        )

        labels.append(
            {
                "x": min_x,
                "y": max_y,
                "xref": "x",
                "yref": "y",
                "text": _group_label(info),
                "showarrow": False,
                "xanchor": "left",
                "yanchor": "bottom",
                "font": {"size": 12, "color": line_color},
                "bgcolor": "rgba(255, 255, 255, 0.6)",
            }
        )

    return shapes, labels


def _find_incorrect_group_overlaps(
    pos: Dict[str, Tuple[float, float]],
    group_infos: Dict[int, Dict[str, Any]],
) -> Set[Tuple[str, str]]:
    """Return nodes that would appear inside unrelated groups."""

    incorrect: Set[Tuple[str, str]] = set()
    for info in group_infos.values():
        if info["parent"] is None:
            continue
        bounds = _group_bounds(info, pos)
        if bounds is None:
            continue
        min_x, max_x, min_y, max_y = bounds
        for node_id, (x, y) in pos.items():
            if node_id in info["nodes"]:
                continue
            if min_x <= x <= max_x and min_y <= y <= max_y:
                incorrect.add((node_id, _group_label(info)))
    return incorrect


def plot_df_graph_groups(
    world: World | AsyncWorld,
    show_plot: bool = False,
    *,
    html_folder: str | None = None,
    max_layout_tries: int = 25,
    accept_incorrectly_placed_simulators: bool = False,
) -> go.Figure:
    """Return a Plotly figure of the dataflow graph with group overlays.

    The layout is retried until no simulator is placed inside an
    unrelated group. Set ``accept_incorrectly_placed_simulators``
    to ``True`` to keep the last attempt even if misplacements
    remain after ``max_layout_tries``.
    """

    import networkx as nx
    import plotly.graph_objects as go

    graph = _build_dataflow_graph(world)
    max_tries = max(1, max_layout_tries)
    group_infos = _collect_group_infos(world)
    pos: Dict[str, Tuple[float, float]] = {}
    incorrect_overlaps: Set[Tuple[str, str]] = set()

    for _attempt in range(max_tries):
        pos = nx.spring_layout(graph)
        incorrect_overlaps = _find_incorrect_group_overlaps(pos, group_infos)
        if not incorrect_overlaps:
            break
    else:
        misplaced = ", ".join(
            sorted(f"{node} in {group}" for node, group in incorrect_overlaps)
        )
        if accept_incorrectly_placed_simulators:
            logger.info(
                "Accepting layout even though following simulators are misplaced: "
                "f{misplaced}. (Accepting due to accept_incorrectly_placed_simulators="
                "True.)"
            )
        else:
            raise RuntimeError(
                "Could not place simulators outside unrelated groups after "
                f"{max_tries} attempts. Misplaced nodes: {misplaced}. "
                "Pass accept_incorrectly_placed_simulators=True to keep the last "
                "layout."
            )

    edge_traces, edge_annotations = _edge_traces(graph, pos)
    node_trace = _node_trace(pos)
    group_shapes, group_labels = _group_shapes(world, pos)

    fig = go.Figure(data=edge_traces + [node_trace])
    fig.update_layout(
        showlegend=False,
        hovermode="closest",
        margin={"b": 0, "l": 0, "r": 0, "t": 0},
        annotations=group_labels + edge_annotations,
        xaxis={"showgrid": False, "zeroline": False},
        yaxis={"showgrid": False, "zeroline": False},
        shapes=group_shapes,
    )
    if html_folder is not None:
        fig.write_html(
            html_folder + "/dataflow_graph_plotly.html", include_plotlyjs="cdn"
        )
    if show_plot:
        fig.show()
    return fig


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

    sims = world._get_sim_runners()
    steps_st: Dict[SimId, List[float]] = {}
    for sim_name in sims.keys():
        steps_st[sim_name] = []

    for node in all_nodes:
        sim_name, tiered_time = node[0]
        steps_st[sim_name].append(_tiered_time_pos(tiered_time))

    fig, ax = plt.subplots()
    if title:
        fig.suptitle(title)

    # Draw the time steps from the simulators
    number_of_steps = 0
    colormap = ["black" for _ in sims]
    for i, sim_name in enumerate(sims):
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
    ax.set_yticks(list(range(len(sims.keys()))))
    ax.set_yticklabels(list(sims.keys()))

    all_edges = list(world.execution_graph.edges())
    y_pos: Dict[SimId, int] = {}
    for sim_count, sim_name in enumerate(sims.keys()):
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
    for sim in world._get_sim_runners().values():
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
