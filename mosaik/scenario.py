"""
This module provides the interface for users to create simulation scenarios for
mosaik.

The :class:`World` holds all necessary data for the simulation and allows the
user to start simulators. It provides a :class:`ModelFactory` (and
a :class:`ModelMock`) via which the user can instantiate model instances
(*entities*). The method :meth:`World.run()` finally starts the simulation.
"""
from __future__ import annotations

import asyncio
from collections import defaultdict
import itertools
from loguru import logger
import networkx
from tqdm import tqdm
from typing import (
    Any,
    Dict,
    Iterable,
    List,
    Optional,
    Set,
    Tuple,
    Union,
    TYPE_CHECKING,
)
from typing_extensions import Literal, TypedDict

from mosaik import simmanager
from mosaik import scheduler
from mosaik.exceptions import ScenarioError, SimulationError


base_config = {
    'addr': ('127.0.0.1', 5555),
    'start_timeout': 10,  # seconds
    'stop_timeout': 10,  # seconds
}

FULL_ID = simmanager.FULL_ID


if TYPE_CHECKING:
    Attr = str
    """An attribute name"""
    SimId = str
    """A simulator ID"""
    EntityId = str
    """An entity ID"""
    FullId = str
    """A full ID of the form "sim_id.entity_id" """
    InputData = Dict[EntityId, Dict[Attr, Dict[FullId, Any]]]
    """The format of input data for simulator's step methods."""
    OutputData = Dict[EntityId, Dict[Attr, Any]]
    """The format of output data as return by `get_data`"""

    class ModelDescription(TypedDict):
        """Description of a single model in `Meta`"""
        public: bool
        """Whether the model can be created directly."""
        params: List[str]
        """The parameters given during creating of this model."""
        any_inputs: bool
        """Whether this model accepts inputs other than those specified in `attrs`."""
        attrs: List[Attr]
        """The input and output attributes of this model."""
        trigger: Iterable[Attr]
        """The input attributes that trigger a step of the associated simulator.

        (Non-trigger attributes are collected and supplied to the simulator when it
        steps next.)"""
        persistent: Iterable[Attr]
        """The output attributes that are persistent."""

    class Meta(TypedDict):
        """The meta-data for a simulator."""
        api_version: str
        """The API version that this simulator supports in the format "major.minor"."""
        old_api: bool
        """Whether this simulator uses the old API (without the `max_advance` parameter
        in `step`. Only used internally. Optional, if unset, treat as `false`."""
        type: Literal['time-based', 'event-based', 'hybrid']
        """The simulator's stepping type."""
        models: Dict[str, ModelDescription]
        """The descriptions of this simulator's models."""
        extra_methods: List[str]
        """The extra methods this simulator supports."""

    class ModelOptionals(TypedDict, total=False):
        env: Dict[str, str]
        """The environment variables to set for this simulator."""
        cwd: str
        """The current working directory for this simulator."""

    class PythonModel(ModelOptionals):
        python: str
        """The Simulator subclass for this simulator, encoded as a string
        `module_name:ClassName`."""

    class ConnectModel(ModelOptionals):
        connect: str
        """The `host:port` address for this simulator."""

    class CmdModel(ModelOptionals):
        cmd: str
        """The command to start this simulator. String %(python)s will be replaced
        by the python command used to start this scenario, %(addr)s will be replaced
        by the `host:port` combination to which the simulator should connect."""

    SimConfig = Dict[str, Union[PythonModel, ConnectModel, CmdModel]]

    # The events can be unset. By splitting them into their own class, we
    # can make them optional.
    class DataflowEgdeOptionals(TypedDict):
        wait_event: asyncio.Event
        """Event on which destination simulator is waiting for its inputs."""
        wait_lazy: asyncio.Event
        """Event on which source simulator is waiting in case of lazy stepping."""
        wait_async: asyncio.Event
        """Event on which source simulator is waiting to support async requests."""

    class DataflowEdge(DataflowEgdeOptionals):
        """The information associated with an edge in the dataflow graph."""
        async_requests: bool
        """Whether there can be async requests along this edge."""
        time_shifted: bool
        """Whether dataflow along this edge is time shifted."""
        weak: bool
        """Whether this edge is weak (used for same-time loops)."""
        trigger: Set[Tuple[EntityId, Attr]]
        """Those pairs of entities and attributes of the source simulator that can
        trigger a step of the destination simulator."""
        pred_waiting: bool
        """Whether the source simulator of this edge has to wait for the destination
        simulator."""
        cached_connections: Iterable[Tuple[EntityId, EntityId, Iterable[Tuple[Attr, Attr]]]]
        dataflows: Iterable[Tuple[EntityId, EntityId, Iterable[Tuple[Attr, Attr]]]]


class World(object):
    """
    The world holds all data required to specify and run the scenario.

    It provides a method to start a simulator process (:meth:`start()`) and
    manages the simulator instances.

    You have to provide a *sim_config* which tells the world which simulators
    are available and how to start them. See :func:`mosaik.simmanager.start()`
    for more details.

    *mosaik_config* can be a dict or list of key-value pairs to set addional
    parameters overriding the defaults::

        {
            'addr': ('127.0.0.1', 5555),
            'start_timeout': 2,  # seconds
            'stop_timeout': 2,   # seconds
        }

    Here, *addr* is the network address that mosaik will bind its socket to.
    *start_timeout* and *stop_timeout* specifiy a timeout (in seconds) for
    starting/stopping external simulator processes.

    If *execution_graph* is set to ``True``, an execution graph will be created
    during the simulation. This may be useful for debugging and testing. Note,
    that this increases the memory consumption and simulation time.
    """

    until: int
    """The time until which this simulation will run."""
    rt_factor: Optional[float]
    """The number of real-time seconds corresponding to one mosaik step."""
    sim_progress: float
    """The progress of the entire simulation (in percent)."""
    _df_cache: Optional[Dict[int, Dict[SimId, Dict[EntityId, Dict[Attr, Any]]]]]
    """Cache for faster dataflow. (Used if `cache=True` is set during World creation."""
    loop: asyncio.AbstractEventLoop
    incoming_connections_queue: asyncio.Queue[Tuple[asyncio.StreamReader, asyncio.StreamWriter]]
    sims: Dict[SimId, simmanager.SimRunner]
    """A dictionary of already started simulators instances."""

    def __init__(
        self,
        sim_config: SimConfig,
        mosaik_config=None,
        time_resolution: float = 1.,
        debug: bool = False,
        cache: bool = True,
        max_loop_iterations: int = 100,
        asyncio_loop: Optional[asyncio.AbstractEventLoop] = None,
    ):
        self.sim_config = sim_config
        """The config dictionary that tells mosaik how to start a simulator."""

        self.config = dict(base_config)
        """The config dictionary for general mosaik settings."""
        if mosaik_config:
            self.config.update(mosaik_config)

        self.time_resolution = time_resolution
        """An optional global *time_resolution* (in seconds) for the scenario,
        which tells the simulators what the integer time step means in seconds.
        Its default value is 1., meaning one integer step corresponds to one
        second simulated time."""

        self.max_loop_iterations = max_loop_iterations

        self.sims = {}

        if asyncio_loop:
            self.loop = asyncio_loop
        else:
            self.loop = asyncio.new_event_loop()

        # When simulators are started using `cmd`, they will connect
        # back to mosaik using a TCP connection. Here we start the
        # server that accepts these connections. Whenever an external
        # simulator connects, the (reader, writer) pair is written to
        # the incoming_connections_queue so that the function starting
        # the simulator can .get() the connection information.
        async def setup_queue():
            return asyncio.Queue()
        self.incoming_connections_queue = self.loop.run_until_complete(setup_queue())

        async def connected_cb(reader, writer):
            await self.incoming_connections_queue.put((reader, writer))

        self.server = self.loop.run_until_complete(
            asyncio.start_server(
                connected_cb,
                self.config['addr'][0],
                self.config['addr'][1],
            )
        )

        self.df_graph = networkx.DiGraph()
        """The directed data-flow :func:`graph <networkx.DiGraph>` for this
        scenario."""

        self.trigger_graph = networkx.DiGraph()
        """The directed :func:`graph <networkx.DiGraph>` from all triggering
        connections for this scenario."""

        self.entity_graph = networkx.Graph()
        """The :func:`graph <networkx.Graph>` of related entities. Nodes are
        ``(sid, eid)`` tuples.  Each note has an attribute *entity* with an
        :class:`Entity`."""

        self.sim_progress = 0
        """Progress of the current simulation (in percent)."""

        self._debug = False
        if debug:
            self._debug = True
            self.execution_graph = networkx.DiGraph()

        # Contains ID counters for each simulator type.
        self._sim_ids = defaultdict(itertools.count)
        # List of outputs for each simulator and model:
        # _df_outattr[sim_id][entity_id] = [attr_1, attr2, ...]
        self._df_outattr = defaultdict(lambda: defaultdict(list))
        if cache:
            self.persistent_outattrs = defaultdict(lambda: defaultdict(list))
            # Cache for simulation results
            self._df_cache = defaultdict(dict)
            self._df_cache_min_time = 0
        else:
            self.persistent_outattrs = {}
            self._df_cache = None

    def start(self, sim_name: str, **sim_params) -> ModelFactory:
        """
        Start the simulator named *sim_name* and return a
        :class:`ModelFactory` for it.
        """
        counter = self._sim_ids[sim_name]
        sim_id = '%s-%s' % (sim_name, next(counter))
        logger.info(
            'Starting "{sim_name}" as "{sim_id}" ...',
            sim_name=sim_name,
            sim_id=sim_id,
        )
        sim = self.loop.run_until_complete(
            simmanager.start(self, sim_name, sim_id, self.time_resolution, sim_params)
        )
        self.sims[sim_id] = sim
        self.df_graph.add_node(sim_id)
        self.trigger_graph.add_node(sim_id)
        return ModelFactory(self, sim)

    def connect(
        self,
        src: Entity,
        dest: Entity,
        *attr_pairs: Union[str, Tuple[str, str]],
        async_requests: bool = False,
        time_shifted: bool = False,
        initial_data: Dict[Attr, Any] = {},
        weak: bool = False
    ):
        """
        Connect the *src* entity to *dest* entity.

        Establish a data-flow for each ``(src_attr, dest_attr)`` tuple in
        *attr_pairs*. If *src_attr* and *dest_attr* have the same name, you
        you can optionally only pass one of them as a single string.

        Raise a :exc:`~mosaik.exceptions.ScenarioError` if both entities share
        the same simulator instance, if at least one (src. or dest.) attribute
        in *attr_pairs* does not exist, or if the connection would introduce
        a cycle in the data-flow (e.g., A → B → C → A).

        If the *dest* simulator may make asynchronous requests to mosaik to
        query data from *src* (or set data to it), *async_requests* should be
        set to ``True`` so that the *src* simulator stays in sync with *dest*.

        An alternative to asynchronous requests are time-shifted connections.
        Their data flow is always resolved after normal connections so that
        cycles in the data-flow can be realized without introducing deadlocks.
        For such a connection *time_shifted* should be set to ``True`` and
        *initial_data* should contain a dict with input data for the first
        simulation step of the receiving simulator.

        An alternative to using async_requests to realize cyclic data-flow
        is given by the time_shifted kwarg. If set to ``True`` it marks the
        connection as cycle-closing (e.g. C → A). It must always be used with
        initial_data specifying a dict with the data sent to the destination
        simulator at the first step (e.g. *{‘src_attr’: value}*).
        """
        if src.sid == dest.sid:
            raise ScenarioError('Cannot connect entities sharing the same '
                                'simulator.')
        if async_requests:
            logger.warning(
                'DEPRECATION: Connections with async_request connections are and will '
                'be removed with set_data() in future releases. Use time_shifted and '
                'weak connections instead'
            )

        if async_requests and time_shifted:
            raise ScenarioError('Async_requests and time_shifted connections '
                                'are incongruous methods for handling of cyclic '
                                'data-flow. Choose one!')

        if self.df_graph.has_edge(src.sid, dest.sid):
            for ctype in ['time_shifted', 'async_requests', 'weak']:
                if eval(ctype) != self.df_graph[src.sid][dest.sid][ctype]:
                    raise ScenarioError(f'{ctype.capitalize()} and standard '
                                        'connections are mutually exclusive, '
                                        'but you have set both between '
                                        f'simulators {src.sid} and {dest.sid}')

        # Expand single attributes "attr" to ("attr", "attr") tuples:
        expanded_attrs = tuple((a, a) if isinstance(a, str) else a for a in attr_pairs)

        missing_attrs = self._check_attributes(src, dest, expanded_attrs)
        if missing_attrs:
            raise ScenarioError('At least one attribute does not exist: %s' %
                                ', '.join('%s.%s' % x for x in missing_attrs))

        # Check dataflow connection (non-)persistent --> (non-)trigger
        self._check_attributes_values(src, dest, expanded_attrs)

        if self._df_cache is not None:
            trigger, cached, time_buffered, memorized, persistent = \
                self._classify_connections_with_cache(src, dest, expanded_attrs)
        else:
            trigger, time_buffered, memorized, persistent = \
                self._classify_connections_without_cache(src, dest, expanded_attrs)
            cached = []

        if time_shifted:
            if type(initial_data) is not dict or initial_data == {}:
                raise ScenarioError('Time shifted connections have to be '
                                    'set with default inputs for the first step.')
            # list for assertion of correct assignment:
            check_attrs = [a[0] for a in expanded_attrs]
            # Set default values for first data exchange:
            for attr, val in initial_data.items():
                if attr not in check_attrs:
                    raise ScenarioError('Incorrect attr "%s" in "initial_data".'
                                        % attr)

                if self._df_cache is not None:
                    self._df_cache[-1].setdefault(src.sid, {})
                    self._df_cache[-1][src.sid].setdefault(src.eid, {})
                    self._df_cache[-1][src.sid][src.eid][attr] = val

        pred_waiting = async_requests

        trigger = set()
        for src_attr, dest_attr in expanded_attrs:
            if (dest.triggered_by(dest_attr)):
                trigger.add((src.eid, src_attr))

        try:
            edge = self.df_graph[src.sid][dest.sid]
            edge['trigger'].update(trigger)
            edge['weak'] = edge['weak'] and weak
            edge['time_shifted'] = edge['time_shifted'] and time_shifted
            edge['async_requests'] = edge['async_requests'] or async_requests
            edge['pred_waiting'] = edge['pred_waiting'] or pred_waiting
        except KeyError:
            async def create_events():
                wait_event = asyncio.Event()
                wait_event.set()
                wait_lazy = asyncio.Event()
                wait_lazy.set()
                wait_async = asyncio.Event()
                wait_async.set()
                return wait_event, wait_lazy, wait_async
            wait_event, wait_lazy, wait_async = self.loop.run_until_complete(create_events())
            self.df_graph.add_edge(
                src.sid,
                dest.sid,
                async_requests=async_requests,
                time_shifted=time_shifted,
                weak=weak,
                trigger=trigger,
                pred_waiting=pred_waiting,
                wait_event=wait_event,
                wait_lazy=wait_lazy,
                wait_async=wait_async,
            )

        dfs = self.df_graph[src.sid][dest.sid].setdefault('dataflows', [])
        dfs.append((src.eid, dest.eid, expanded_attrs))

        cached_connections = self.df_graph[src.sid][dest.sid].setdefault(
            'cached_connections', [])
        if cached:
            cached_connections.append((src.eid, dest.eid, cached))

        # Add relation in entity_graph
        self.entity_graph.add_edge(src.full_id, dest.full_id)

        # Cache the attribute names which we need output data for after a
        # simulation step to reduce the number of df graph queries.
        outattr = [a[0] for a in expanded_attrs]
        if outattr:
            self._df_outattr[src.sid][src.eid].extend(outattr)

        for src_attr, dest_attr in time_buffered:
            src.sim.buffered_output.setdefault((src.eid, src_attr), []).append(
                (dest.sid, dest.eid, dest_attr))

        if weak:
            for src_attr, dest_attr in persistent:
                try:
                    dest.sim.input_buffer.setdefault(dest.eid, {}).setdefault(
                        dest_attr, {})[
                        FULL_ID % (src.sid, src.eid)] = initial_data[src_attr]
                except KeyError:
                    raise ScenarioError('Weak connections of persistent '
                                        'attributes have to be set with '
                                        'default inputs for the first step. '
                                        f'{src_attr} is missing for connection'
                                        f' from {FULL_ID % (src.sid, src.eid)} '
                                        f'to {FULL_ID % (dest.sid, dest.eid)}.')

        for src_attr, dest_attr in memorized:
            if weak or time_shifted:
                init_val = initial_data[src_attr]
            else:
                init_val = None
            dest.sim.input_memory.setdefault(dest.eid, {}).setdefault(
                dest_attr, {})[FULL_ID % (src.sid, src.eid)] = init_val

    def set_initial_event(self, sid: SimId, time: int = 0):
        """
        Set an initial step for simulator *sid* at time *time* (default=0).
        """
        self.sims[sid].next_steps = [time]

    def get_data(
        self,
        entity_set: Iterable[Entity],
        *attributes: Attr,
    ) -> Dict[Entity, Dict[Attr, Any]]:
        """
        Get and return the values of all *attributes* for each entity of an
        *entity_set*.

        The return value is a dict mapping the entities of *entity_set* to
        dicts containing the values of each attribute in *attributes*::

            {
                Entity(...): {
                    'attr_1': 'val_1',
                    'attr_2': 'val_2',
                    ...
                },
                ...
            }
        """
        outputs_by_sim = defaultdict(dict)
        for entity in entity_set:
            outputs_by_sim[entity.sid][entity.eid] = attributes

        async def request_data():
            requests = {
                sid: asyncio.create_task(self.sims[sid].proxy.get_data(outputs))
                for sid, outputs in outputs_by_sim.items()
            }
            try:
                await asyncio.gather(*requests.values())
            except ConnectionError as e:
                # Try to find the simulator that closed its connection
                for sid, task in requests.items():
                    if task.exception():
                        raise SimulationError(
                            f"Simulator '{sid}' closed its connection while executing "
                            "`World.get_data()`.",
                            e,
                        ) from None
                else:
                    raise RuntimeError(
                        "Could not determine which simulator closed its connection."
                    )

            results_by_sim = {}
            for sid, task in requests.items():
                results_by_sim[sid] = task.result()

            return results_by_sim

        results_by_sim = self.loop.run_until_complete(request_data())
        results = {}
        for entity in entity_set:
            results[entity] = results_by_sim[entity.sid][entity.eid]

        return results

    def run(
        self,
        until: int,
        rt_factor: Optional[float] = None,
        rt_strict: bool = False,
        print_progress: Union[bool, Literal["individual"]] = True,
        lazy_stepping: bool = True,
    ):
        """
        Start the simulation until the simulation time *until* is reached.

        In order to perform real-time simulations, you can set *rt_factor* to
        a number > 0. A rt-factor of 1. means that 1 second in simulated time
        takes 1 second in real-time. An rt-factor 0f 0.5 will let the
        simulation run twice as fast as real-time. For correct behavior of the
        rt_factor the time_resolution of the scenario has to be set adequately,
        which is 1. [second] by default.

        If the simulators are too slow for the rt-factor you chose, mosaik
        prints by default only a warning. In order to raise
        a :exc:`RuntimeError`, you can set *rt_strict* to ``True``.

        ``print_progress`` controls whether progress bars are printed while the
        simulation is running. The default is to print one bar representing the
        global progress of the simulation. You can also set
        ``print_progress='individual'`` to get one bar per simulator in your
        simulation (in addition to the global one). ``print_progress=False`
        turns off the progress bars completely. The progress bars use
        `tqdm <https://pypi.org/project/tqdm/>`_; see their documentation
        on how to write to the console without interfering with the bars.

        You can also set the *lazy_stepping* flag (default: ``True``). If
        ``True`` a simulator can only run ahead one step of it's successors. If
        ``False`` a simulator always steps as long all input is provided. This
        might decrease the simulation time but increase the memory consumption.

        Before this method returns, it stops all simulators and closes mosaik's
        server socket. So this method should only be called once.
        """
        if self.loop.is_closed():
            raise RuntimeError(
                "Simulation has already been run and can only be run once for a World "
                "instance."
            )

        # Check if a simulator is not connected to anything:
        for sid, deg in sorted(list(networkx.degree(self.df_graph))):
            if deg == 0:
                logger.warning('{sim_id} has no connections.', sim_id=sid)

        self.detect_unresolved_cycles()

        trigger_edges = [(u, v) for (u, v, w) in self.df_graph.edges.data(True)
                         if w['trigger']]
        self.trigger_graph.add_edges_from(trigger_edges)

        self.cache_trigger_cycles()
        self.cache_dependencies()
        self.cache_related_sims()
        self.cache_triggering_ancestors()
        self.create_simulator_ranking()

        logger.info('Starting simulation.')
        # 11 is the length of "Total: 100%"
        max_sim_id_len = max(max(len(str(sid)) for sid in self.sims), 11)
        until_len = len(str(until))
        self.tqdm = tqdm(
            total=until,
            disable=not print_progress,
            colour='green',
            bar_format=(
                None
                if print_progress != 'individual'
                else (
                    "Total:%s {percentage:3.0f}%% |{bar}| %s{elapsed}<{remaining}" %
                    (" " * (max_sim_id_len - 11), "  " * until_len)
                )
            ),
            unit='steps',
        )
        for sid, sim in self.sims.items():
            sim.tqdm = tqdm(
                total=until,
                desc=sid,
                bar_format=(
                    "{desc:>%i} |{bar}| {n_fmt:>%i}/{total_fmt}{postfix:10}" %
                    (max_sim_id_len, until_len)
                ),
                leave=False,
                disable=print_progress != 'individual',
            )
        import mosaik._debug as dbg  # always import, enable when requested
        if self._debug:
            dbg.enable()
        success = False
        try:
            self.loop.run_until_complete(scheduler.run(
                self, until, rt_factor, rt_strict, lazy_stepping
            ))
            success = True
        except KeyboardInterrupt:
            logger.info('Simulation canceled. Terminating ...')
        finally:
            for sid, sim in self.sims.items():
                sim.tqdm.close()
            self.tqdm.close()
            self.shutdown()
            if self._debug:
                dbg.disable()
            if success:
                logger.info('Simulation finished successfully.')

    def detect_unresolved_cycles(self):
        """
        Searches for unresolved cycles, i.e. cycles that do not have a weak or
        time_shifted connection. Raises an error if an unresolved cycle is found.
        """
        cycles = list(networkx.simple_cycles(self.df_graph))
        for cycle in cycles:
            sim_pairs = list(zip(cycle, cycle[1:] + [cycle[0]]))
            self._detect_missing_loop_breakers(cycle, sim_pairs)

    def _detect_missing_loop_breakers(
        self,
        cycle: List[SimId],
        sim_pairs: List[Tuple[SimId, SimId]],
    ):
        """
        Searches for loop breakers, i.e. weak or time_shifted connections in
        a loop. If no such loop breaker is present, the cycle is unresolved
        and an error is raised.
        """
        loop_breaker = [
            self.df_graph[src_id][dest_id]["weak"]
            or self.df_graph[src_id][dest_id]["time_shifted"]
            for src_id, dest_id in sim_pairs
        ]
        if not any(loop_breaker):
            raise ScenarioError(
                "Scenario has unresolved cyclic "
                f"dependencies: {sorted(cycle)}. Use options "
                '"time-shifted" or "weak" for resolution.'
            )

    def cache_trigger_cycles(self):
        """
        For all simulators, if they are part of a cycle, add information
        about trggers in the cycle(s) to the simulator object
        """
        # Get the cycles from the networkx package
        cycles = list(networkx.simple_cycles(self.trigger_graph))
        # For every simulator go through all cycles in which the simulator is a node
        for sim in self.sims.values():
            for cycle in cycles:
                if sim.sid in cycle:
                    index_of_simulator = cycle.index(sim.sid)
                    successor_sid, cycle_edges = self._get_cycle_info(
                        cycle, index_of_simulator
                    )
                    ingoing_edge, outgoing_edge = self._get_in_out_edges(
                        index_of_simulator, cycle_edges
                    )
                    sids: List[SimId] = sorted(cycle)
                    # If connections between simulators are time-shifted, the cycle
                    # needs more time for a trigger round. If no edge is timeshifted,
                    # the minimum length is 0.
                    min_length: int = sum(
                        [edge["time_shifted"] for edge in cycle_edges]
                    )
                    trigger_cycle = simmanager.TriggerCycle(
                        sids=sids,
                        activators=outgoing_edge["trigger"],
                        min_length=min_length,
                        in_edge=ingoing_edge,
                        time=-1,
                        count=0,
                    )
                    # Store the trigger cycle in the simulation object
                    sim.trigger_cycles.append(trigger_cycle)

    def _get_cycle_info(
        self,
        cycle: List[SimId],
        index_of_simulator: int,
    ) -> Tuple[SimId, List[DataflowEdge]]:
        """
        Returns the sid of the successor and all the edges from the cycle.
        """
        # Combine the ids of the cycle elements to get the edge ids and edges
        edge_ids = list(zip(cycle, cycle[1:] + [cycle[0]]))
        successor_sid = edge_ids[index_of_simulator][1]
        cycle_edges = [
            self.df_graph.get_edge_data(src_id, dest_id) for src_id, dest_id in edge_ids
        ]
        return successor_sid, cycle_edges  # type: ignore

    def _get_in_out_edges(
        self,
        index_of_simulator: int,
        cycle_edges: List[DataflowEdge],
    ) -> Tuple[DataflowEdge, DataflowEdge]:
        """
        Returns the ingoing and outgoing edge in the cycle from the given simulator
        """
        ingoing_edge = cycle_edges[(index_of_simulator - 1) % len(cycle_edges)]
        outgoing_edge = cycle_edges[index_of_simulator]
        return ingoing_edge, outgoing_edge

    def cache_dependencies(self):
        """
        Loops through all simulations and adds predecessors and successors to the
        simulations.
        """
        for sid, sim in self.sims.items():
            sim.predecessors = {}
            for pre_sid in self.df_graph.predecessors(sid):
                pre_sim = self.sims[pre_sid]
                edge = self.df_graph[pre_sid][sid]
                sim.predecessors[pre_sid] = (pre_sim, edge)

            sim.successors = {}
            for suc_sid in self.df_graph.successors(sid):
                suc_sim = self.sims[suc_sid]
                edge = self.df_graph[sid][suc_sid]
                sim.successors[suc_sid] = (suc_sim, edge)

    def cache_related_sims(self):
        """
        Stores the related simulators for a simulator in the simulator object.
        The related simulators are all simulators in the scenario that are not
        the simulator itself.
        """
        all_sims = self.sims.values()
        for sim in all_sims:
            sim.related_sims = [isim for isim in all_sims if isim != sim]

    def cache_triggering_ancestors(self):
        """
        Collects the ancestors of each simulator and stores them in the
        respective simulator object.
        """
        for sim in self.sims.values():
            triggering_ancestors = sim.triggering_ancestors = []
            ancestors = list(networkx.ancestors(self.trigger_graph, sim.sid))
            for ancestors_sid in ancestors:
                distance = self._get_shortest_distance_from_edges(sim, ancestors_sid)
                is_immediate_connection: bool = distance == 0
                triggering_ancestors.append((ancestors_sid, is_immediate_connection))

    def _get_shortest_distance_from_edges(
        self,
        simulator: simmanager.SimRunner,
        ancestors_sid: str,
    ) -> int:
        """
        Returns the minimum distance of all edges on the paths from the
        ancestors to the given simulator.
        """
        paths = networkx.all_simple_edge_paths(
            self.trigger_graph, ancestors_sid, simulator.sid
        )
        distances = []
        for edges in paths:
            distance = 0
            for edge in edges:
                edge = self.df_graph[edge[0]][edge[1]]
                distance += edge["time_shifted"] or edge["weak"]
            distances.append(distance)
        return min(distances)

    def create_simulator_ranking(self):
        """
        Deduce a simulator ranking from a topological sort of the df_graph.
        """
        graph_tmp = self.df_graph.copy()
        loop_edges = [(u, v) for (u, v, w) in graph_tmp.edges.data(True) if
                      w['time_shifted'] or w['weak']]
        graph_tmp.remove_edges_from(loop_edges)
        topo_sort = list(networkx.topological_sort(graph_tmp))
        for rank, sid in enumerate(topo_sort):
            self.sims[sid].rank = rank

    def shutdown(self):
        """
        Shut-down all simulators and close the server socket.
        """
        if self.loop.is_closed():
            return

        for sim in self.sims.values():
            self.loop.run_until_complete(sim.stop())

        self.server.close()
        self.loop.close()

    def _check_attributes(
        self,
        src: Entity,
        dest: Entity,
        attr_pairs: Iterable[Tuple[Attr, Attr]],
    ) -> Iterable[Tuple[Entity, Attr]]:
        """
        Check if *src* and *dest* have the attributes in *attr_pairs*.

        Raise a :exc:`~mosaik.exceptions.ScenarioError` if an attribute does
        not exist. Exception: If the meta data for *dest* declares
        ``'any_inputs': True``.
        """
        attr_errors = []
        for src_attr, dest_attr in attr_pairs:
            if src_attr not in src.meta['attrs']:
                attr_errors.append((src, src_attr))
            if not (dest.meta['any_inputs'] or dest_attr in dest.meta['attrs']):
                attr_errors.append((dest, dest_attr))
        return attr_errors

    def _check_attributes_values(
        self,
        src: Entity,
        dest: Entity,
        attr_pairs: Iterable[Tuple[Attr, Attr]],
    ):
        """
        Check if *src* and *dest* attributes in *attr_pairs* are a combination of
        persistent and trigger or non-persistent and non-trigger.

        """
        non_persistent = set(src.meta['attrs']).difference(src.meta['persistent'])
        non_trigger = set(dest.meta['attrs']).difference(dest.meta['trigger'])
        for src_attr, dest_attr in attr_pairs:
            if (dest_attr in non_trigger) and (src_attr in non_persistent):
                logger.warning(
                    'A connection between non-persistent ({src_sid}:{src_attr}) and non-trigger ({dest_sid}:{dest_attr}) '
                    'attributes is not recommended. This might cause problems in the simulation! See also: '
                    'https://mosaik.readthedocs.io/en/latest/scenario-definition.html#connecting-entities',
                    src_attr=src_attr, dest_attr=dest_attr, src_sid=src.sim.sid, dest_sid=dest.sim.sid
                )

    def _classify_connections_with_cache(
        self,
        src: Entity,
        dest: Entity,
        attr_pairs: Iterable[Tuple[Attr, Attr]],
    ) -> Tuple[
        bool,
        Iterable[Tuple[Attr, Attr]],
        Iterable[Tuple[Attr, Attr]],
        Iterable[Tuple[Attr, Attr]],
        Iterable[Tuple[Attr, Attr]],
    ]:
        """
        Classifies the connection by analyzing the model's meta data with
        enabled cache, i.e. if it triggers a step of the destination, how the
        data is cached, and if it's persistent and need's to be saved in the
         input_memory.
        """
        any_trigger = False
        cached = []
        time_buffered = []
        memorized = []
        persistent = []

        for attr_pair in attr_pairs:
            src_attr, dest_attr = attr_pair
            trigger = (dest_attr in dest.meta['trigger'] or (
                dest.meta['any_inputs'] and dest.sim.proxy.meta['type'] == 'event-based'))
            if trigger:
                any_trigger = True

            is_persistent = src_attr in src.meta['persistent']
            if is_persistent:
                persistent.append(attr_pair)
            if src.sim.proxy.meta['type'] != 'time-based':
                time_buffered.append(attr_pair)
                if is_persistent:
                    memorized.append(attr_pair)
            else:
                cached.append(attr_pair)
        return (any_trigger, tuple(cached), tuple(time_buffered),
                tuple(memorized), tuple(persistent))

    def _classify_connections_without_cache(
        self,
        src: Entity,
        dest: Entity,
        attr_pairs: Iterable[Tuple[Attr, Attr]],
    ) -> Tuple[
        bool,
        Iterable[Tuple[Attr, Attr]],
        Iterable[Tuple[Attr, Attr]],
        Iterable[Tuple[Attr, Attr]],
    ]:
        """
        Classifies the connection by analyzing the model's meta data with
        disabled cache, i.e. if it triggers a step of the destination, if the
        attributes are persistent and need to be saved in the input_memory.
        """
        trigger = False
        persistent = []
        for attr_pair in attr_pairs:
            src_attr, dest_attr = attr_pair
            if (dest_attr in dest.meta['trigger'] or (
                    dest.meta['any_inputs'] and dest.sim.proxy.meta['type'] == 'event-based')):
                trigger = True
            is_persistent = src_attr in src.meta['persistent']
            if is_persistent:
                persistent.append(attr_pair)
        memorized = persistent

        return trigger, tuple(attr_pairs), tuple(memorized), tuple(persistent)


class ModelFactory():
    """
    This is a facade for a simulator *sim* that allows the user to create
    new model instances (entities) within that simulator.

    For every model that a simulator publicly exposes, the ``ModelFactory``
    provides a :class:`ModelMock` attribute that actually creates the entities.

    If you access an attribute that is not a model or if the model is not
    marked as *public*, an :exc:`~mosaik.exceptions.ScenarioError` is raised.
    """

    def __init__(self, world: World, sim: simmanager.SimRunner):
        self.meta = sim.proxy.meta
        self._world = world
        self._sim = sim

        # Create a ModelMock for every public model
        for model, props in self.meta['models'].items():
            if props['public']:
                setattr(self, model, ModelMock(self._world, model, self._sim))

        # Bind extra_methods to this instance:
        for meth_name in self.meta['extra_methods']:
            # We need get_wrapper() in order to avoid problems with scoping
            # of the name "meth". Without it, "meth" would be the same for all
            # wrappers.
            def get_wrapper(sim, meth_name):
                meth = getattr(sim.proxy, meth_name)
                def wrapper(*args, **kwargs):
                    return world.loop.run_until_complete(
                        meth(*args, **kwargs)
                    )
                wrapper.__name__ = meth_name
                return wrapper

            setattr(self, meth_name, get_wrapper(sim, meth_name))

    def __getattr__(self, name):
        # Implemented in order to improve error messages.
        models = self.meta['models']
        if name in models and not models[name]['public']:
            raise AttributeError('Model "%s" is not public.' % name)
        else:
            raise AttributeError('Model factory for "%s" has no model and no '
                                 'function "%s".' % (self._sim.sid, name))


class ModelMock(object):
    """
    Instances of this class are exposed as attributes of
    :class:`ModelFactory` and allow the instantiation of simulator models.

    You can *call* an instance of this class to create exactly one entity:
    ``sim.ModelName(x=23)``. Alternatively, you can use the :meth:`create()`
    method to create multiple entities with the same set of parameters at once:
    ``sim.ModelName.create(3, x=23)``.
    """

    def __init__(self, world: World, name: str, sim: simmanager.SimRunner):
        self._world = world
        self._name = name
        self._sim = sim
        self._sim_id = sim.sid
        self._params = sim.proxy.meta['models'][name]['params']

    def __call__(self, **model_params):
        """
        Call :meth:`create()` to instantiate one model.
        """
        self._check_params(**model_params)
        return self.create(1, **model_params)[0]

    def create(self, num: int, **model_params):
        """
        Create *num* entities with the specified *model_params* and return
        a list with the entity dicts.

        The returned list of entities is the same as returned by
        :meth:`mosaik_api_v3.Simulator.create()`, but the simulator is prepended
        to every entity ID to make them globally unique.
        """
        self._check_params(**model_params)

        entities = self._world.loop.run_until_complete(
            self._sim.proxy.create(num, self._name, **model_params)
        )
        assert len(entities) == num, (
            f'{num} entities were requested but {len(entities)} were created.'
        )

        return self._make_entities(entities, assert_type=self._name)

    def _check_params(self, **model_params):
        expected_params = list(self._params)
        for param in model_params:
            if param not in expected_params:
                raise TypeError("create() got an unexpected keyword argument "
                                "'%s'" % param)
            expected_params.remove(param)

    def _make_entities(self, entity_dicts, assert_type=None):
        """
        Recursively create lists of :class:`Entity` instance from a list
        of *entity_dicts*.
        """
        sim_name = self._sim.name
        sim_id = self._sim_id
        entity_graph = self._world.entity_graph

        entity_set = []
        for e in entity_dicts:
            self._assert_model_type(assert_type, e)

            children = e.get('children', [])
            if children:
                children = self._make_entities(children)
            entity = Entity(sim_id, e['eid'], sim_name, e['type'], children,
                            self._sim)

            entity_set.append(entity)
            entity_graph.add_node(entity.full_id, sim=sim_name, type=e['type'])
            for rel in e.get('rel', []):
                entity_graph.add_edge(entity.full_id, FULL_ID % (sim_id, rel))

        return entity_set

    def _assert_model_type(self, assert_type, e):
        """
        Assert that entity *e* has either type *assert_type* if is not none
        or else any valid type.
        """
        if assert_type is not None:
            assert e['type'] == assert_type, (
                f'Entity "{e["eid"]}" has the wrong type: "{e["type"]}"; '
                f'"{assert_type}" required.'
            )
        else:
            assert e['type'] in self._sim.proxy.meta['models'], (
                f'Type "{e["type"]}" of entity "{e["eid"]}" not found in sim\'s meta '
                'data.'
            )


class Entity(object):
    """
    An entity represents an instance of a simulation model within mosaik.
    """
    __slots__ = ['sid', 'eid', 'sim_name', 'type', 'children', 'sim']
    sid: SimId
    eid: EntityId
    sim_name: str
    type: str
    children: Iterable[Entity]
    sim: simmanager.SimRunner

    def __init__(self, sid, eid, sim_name, type, children, sim):
        self.sid = sid
        """The ID of the simulator this entity belongs to."""

        self.eid = eid
        """The entity's ID."""

        self.sim_name = sim_name
        """The entity's simulator name."""

        self.type = type
        """The entity's type (or class)."""

        self.children = children if children is not None else set()
        """An entity set containing subordinate entities."""

        self.sim = sim
        """The :class:`~mosaik.simmanager.SimProxy` containing the entity."""

    @property
    def full_id(self) -> FullId:
        """
        Full, globally unique entity id ``sid.eid``.
        """
        return FULL_ID % (self.sid, self.eid)

    def triggered_by(self, attr: Attr) -> bool:
        return (attr in self.meta["trigger"]) or (
            self.sim.proxy.meta["type"] == "event-based"
            and self.meta["any_inputs"]
        )

    def is_persistent(self, attr: Attr) -> bool:
        return (attr in self.meta["persistent"])

    @property
    def meta(self) -> ModelDescription:
        return self.sim.proxy.meta['models'][self.type]

    def __str__(self):
        return '%s(%s)' % (self.__class__.__name__, ', '.join([
            repr(self.sid), repr(self.eid), repr(self.sim_name), self.type]))

    def __repr__(self):
        return '%s(%s)' % (self.__class__.__name__, ', '.join([
            repr(self.sid), repr(self.eid), repr(self.sim_name), self.type,
            repr(self.children), repr(self.sim)]))
