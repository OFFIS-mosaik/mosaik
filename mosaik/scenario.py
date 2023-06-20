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
    FrozenSet,
    Iterable,
    List,
    Optional,
    Set,
    Tuple,
    Union,
)
from typing_extensions import Literal, TypedDict

from mosaik_api.connection import Channel
from mosaik_api.types import EntityId, Attr, ModelName, SimId, FullId, ModelDescription

from mosaik import simmanager
from mosaik.proxies import Proxy
from mosaik.simmanager import PredecessorInfo, SimRunner, SuccessorInfo
from mosaik import scheduler
from mosaik.exceptions import ScenarioError, SimulationError


base_config = {
    'addr': ('127.0.0.1', 5555),
    'start_timeout': 10,  # seconds
    'stop_timeout': 10,  # seconds
}

FULL_ID = simmanager.FULL_ID


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


class DataflowEdge(TypedDict):
    """The information associated with an edge in the dataflow graph."""
    async_requests: bool
    """Whether there can be async requests along this edge."""
    time_shifted: int
    """How much dataflow along this edge is time shifted."""
    weak: bool
    """Whether this edge is weak (used for same-time loops)."""
    trigger: Set[Tuple[EntityId, Attr]]
    """Those pairs of entities and attributes of the source simulator that can
    trigger a step of the destination simulator."""
    cached_connections: Iterable[Tuple[EntityId, EntityId, Iterable[Tuple[Attr, Attr]]]]
    wait_event: asyncio.Event
    """Event on which destination simulator is waiting for its inputs."""
    wait_lazy: asyncio.Event
    """Event on which source simulator is waiting in case of lazy stepping."""
    wait_async: asyncio.Event
    """Event on which source simulator is waiting to support async requests."""


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

    time_resolution: float
    """The number of seconds that correspond to one mosaik time step in
    this situation. The default value is 1.0, meaning that one integer
    step corresponds to one second simulated time.
    """
    max_loop_iterations: int
    """The number of iterations allowed for same-time loops within one
    time step. This is checked to prevent accidental infinite loops.
    Increase this value if your same-time loops require many iterations
    to converge.
    """

    sim_progress: float
    """The progress of the entire simulation (in percent)."""
    use_cache: bool
    #use_cache: Optional[Dict[int, Dict[SimId, Dict[EntityId, Dict[Attr, Any]]]]]
    """Cache for faster dataflow. It is used if `cache=True` is set during
    World creation. The four levels of indices are:
    - the time step at which the data is valid
    - the SimId of the source simulator
    - the EntityId of the source simulator
    - the source attribute.
    """
    loop: asyncio.AbstractEventLoop
    incoming_connections_queue: asyncio.Queue[Channel]
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

        self.sims = {}
        self.time_resolution = time_resolution
        self.max_loop_iterations = max_loop_iterations

        if asyncio_loop:
            self.loop = asyncio_loop
        else:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)

        # When simulators are started using `cmd`, they will connect
        # back to mosaik using a TCP connection. Here we start the
        # server that accepts these connections. Whenever an external
        # simulator connects, a Channel is created from the 
        # (reader, writer) pair and written to the 
        # incoming_connections_queue so that the function starting the
        # simulator can .get() the connection information.
        async def setup_queue():
            return asyncio.Queue()
        self.incoming_connections_queue = self.loop.run_until_complete(setup_queue())

        async def connected_cb(reader, writer):
            await self.incoming_connections_queue.put(Channel(reader, writer))

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
        self._trigger_graph = networkx.subgraph_view(self.df_graph,
            filter_edge=lambda s, t: bool(self.df_graph[s][t]["trigger"])
        )

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
        if cache:
            # Cache for simulation results
            self.use_cache = True
            self._df_cache_min_time = 0
        else:
            self.use_cache = False

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
        proxy = self.loop.run_until_complete(
            simmanager.start(self, sim_name, sim_id, self.time_resolution, sim_params)
        )
        self.sims[sim_id] = SimRunner(sim_id, self, proxy)
        self.df_graph.add_node(sim_id)
        return ModelFactory(self, sim_id, proxy)

    def connect(
        self,
        src: Entity,
        dest: Entity,
        *attr_pairs: Union[str, Tuple[str, str]],
        async_requests: bool = False,
        time_shifted: Union[bool, int] = False,
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
        if src.sid == dest.sid and not (time_shifted or weak):
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

        persistent = [
            attr_pair for attr_pair in expanded_attrs if src.is_persistent(attr_pair[0])
        ]

        if not self.use_cache or src.model_mock._factory.type != 'time-based':
            time_buffered = expanded_attrs
            memorized = persistent
            cached = []
        else:
            time_buffered = []
            memorized = []
            cached = expanded_attrs
            

        trigger = set()
        for src_attr, dest_attr in expanded_attrs:
            if (dest.triggered_by(dest_attr)):
                trigger.add((src.eid, src_attr))

        try:
            edge = self.df_graph[src.sid][dest.sid]
            edge['trigger'].update(trigger)
            if not edge['weak'] == weak:
                raise ScenarioError(
                    f"There is already a connection between the simulators {src.sid} "
                    f"and {dest.sid} with weak={edge['weak']}. Further connections "
                    f"must specify the same value, but you gave weak={weak}."
                )
            edge['time_shifted'] = edge['time_shifted'] and time_shifted
            if not edge['time_shifted'] == int(time_shifted):
                raise ScenarioError(
                    f"There is already a connection between the simulators {src.sid} "
                    f"and {dest.sid} with time_shifted={edge['time_shifted']}. Further "
                    f"connections must specify the same value, but you gave "
                    f"time_shifted={time_shifted}."
                )
            edge['async_requests'] = edge['async_requests'] or async_requests
            if cached:
                edge['cached_connections'].append((src.eid, dest.eid, cached))
        except KeyError:
            self.df_graph.add_edge(
                src.sid,
                dest.sid,
                async_requests=async_requests,
                time_shifted=int(time_shifted),
                weak=weak,
                trigger=trigger,
                cached_connections=(
                    [(src.eid, dest.eid, cached)] if cached else []
                ),
            )

        # Add relation in entity_graph
        self.entity_graph.add_edge(src.full_id, dest.full_id)

        # Cache the attribute names which we need output data for after a
        # simulation step to reduce the number of df graph queries.
        outattr = [a[0] for a in expanded_attrs]
        if outattr:
            self.sims[src.sid].output_request.setdefault(src.eid, []).extend(outattr)

        # TODO: Move creation of SimRunners into World.run
        for src_attr, dest_attr in time_buffered:
            src_runner = self.sims[src.sid]
            src_runner.buffered_output.setdefault((src.eid, src_attr), []).append(
                (self.sims[dest.sid], dest.eid, dest_attr))

        # Setting of initial data
        
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

                if self.use_cache:
                    src_sim = self.sims[src.sid]
                    src_sim.outputs[-1].setdefault(src.eid, {})[attr] = val

        if weak:
            for src_attr, dest_attr in persistent:
                try:
                    dest_runner = self.sims[dest.sid]
                    dest_runner.input_buffer.setdefault(dest.eid, {}).setdefault(
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
            dest_runner = self.sims[dest.sid]
            dest_runner.input_memory.setdefault(dest.eid, {}).setdefault(
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
                sid: asyncio.create_task(self.sims[sid].get_data(outputs))
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

        # Creating the topological ranking will ensure that there are no
        # cycles in the dataflow graph that are not resolved using
        # time-shifted or weak connections.
        self.create_simulator_ranking()

        self.cache_trigger_cycles()
        self.cache_dependencies()
        self.cache_related_sims()
        self.cache_triggering_ancestors()

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

    def cache_trigger_cycles(self):
        """
        For all simulators, if they are part of a cycle, add information
        about trggers in the cycle(s) to the simulator object
        """
        # Get the cycles from the networkx package
        cycles = list(networkx.simple_cycles(self._trigger_graph))
        # For every simulator go through all cycles in which the simulator is a node
        for cycle_count, cycle in enumerate(networkx.simple_cycles(self._trigger_graph)):
            if cycle_count == 1000:
                logger.warning(
                    "Your simulation has many cycles of simulators that can trigger "
                    "each other. This can make scenario setup very slow. Usually, "
                    "it is better to create multiple entities in the same simulator "
                    "instead of many simulators with one entity."
                )
            for index_of_simulator, sid in enumerate(cycle):
                successor_sid, cycle_edges = self._get_cycle_info(
                    cycle, index_of_simulator
                )
                ingoing_edge, outgoing_edge = self._get_in_out_edges(
                    index_of_simulator, cycle_edges
                )
                # If connections between simulators are time-shifted, the cycle
                # needs more time for a trigger round. If no edge is time-shifted,
                # the minimum length is 0.
                min_length: int = sum(
                    [edge["time_shifted"] for edge in cycle_edges]
                )
                trigger_cycle = simmanager.TriggerCycle(
                    sids=cycle,
                    activators=outgoing_edge["trigger"],
                    min_length=min_length,
                    in_edge=ingoing_edge,
                    time=-1,
                    count=0,
                )
                # Store the trigger cycle in the simulation object
                self.sims[sid].trigger_cycles.append(trigger_cycle)

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
        return successor_sid, cycle_edges

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
        for pre_sid, suc_sid, edge in self.df_graph.edges(data=True):
            pre_sim = self.sims[pre_sid]
            suc_sim = self.sims[suc_sid]
            wait_event = asyncio.Event()
            wait_event.set()
            wait_lazy = asyncio.Event()
            wait_lazy.set()
            wait_async = asyncio.Event()
            wait_async.set()

            suc_sim.predecessors[pre_sim] = PredecessorInfo(
                time_shift=edge["time_shifted"],
                wait_event=wait_event,
                wait_lazy=wait_lazy,
                wait_async=wait_async,
                cached_connections=edge['cached_connections'],
                triggering=bool(edge["trigger"]),
            )

            pre_sim.successors[suc_sim] = SuccessorInfo(
                time_shift=edge["time_shifted"],
                is_weak=edge["weak"],
                pred_waiting=edge["async_requests"],
                trigger=edge["trigger"],
                wait_event=wait_event,
                wait_lazy=wait_lazy,
                wait_async=wait_async,
            )

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
            ancestors = list(networkx.ancestors(self._trigger_graph, sim.sid))
            for ancestors_sid in ancestors:
                distance = networkx.shortest_path_length(
                    self._trigger_graph, ancestors_sid, sim.sid,
                    weight=lambda src, tgt, edge: edge["time_shifted"] or edge["weak"]
                )
                is_immediate_connection: bool = distance == 0
                triggering_ancestors.append(
                    (self.sims[ancestors_sid], is_immediate_connection)
                )

    def create_simulator_ranking(self):
        """
        Deduce a simulator ranking from a topological sort of the df_graph.
        """
        immediate_graph = networkx.subgraph_view(
            self.df_graph,
            filter_edge=lambda s, t: (
                not self.df_graph[s][t]['time_shifted']
                and not self.df_graph[s][t]['weak']
            )
        )
        try:
            for rank, sid in enumerate(networkx.topological_sort(immediate_graph)):
                self.sims[sid].rank = rank
        except networkx.NetworkXUnfeasible as e:
            # Find a cycle as a counter-example.
            cycle = next(networkx.simple_cycles(immediate_graph))
            raise ScenarioError(
                "Your scenario contains cycles that are not broken up using "
                "time-shifted or weak connections. mosaik is unable to determine which "
                "simulator to run first in these cases. Here is an example of one such "
                f"cycle: {cycle}."
            ) from e

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
            if src_attr not in src.model_mock.output_attrs:
                attr_errors.append((src, src_attr))
            if not (dest.model_mock.any_inputs or dest_attr in dest.model_mock.input_attrs):
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
        for src_attr, dest_attr in attr_pairs:
            if (
                dest_attr in dest.model_mock.event_inputs
                and src_attr in src.model_mock.measurement_outputs
            ):
                logger.warning(
                    f'A connection between the persistent attribute {src_attr} of '
                    f'{src.sid} and the trigger attribute {dest_attr} of {dest.sid} is '
                    f'not recommended. This might cause problems in the simulation!'
                )
            elif (
                dest_attr in dest.model_mock.measurement_inputs
                and src_attr in src.model_mock.event_outputs
            ):
                logger.warning(
                    f'A connection between the non-persistent attribute {src_attr} of '
                    f'{src.sid} and the non-trigger attribute {dest_attr} of '
                    f'{dest.sid} is not recommended. This might cause problems in the '
                    'simulation!'
                )


MOSAIK_METHODS = set(
    ["init", "create", "setup_done", "step", "get_data", "finalize", "stop"]
)


class ModelFactory():
    """
    This is a facade for a simulator *sim* that allows the user to create
    new model instances (entities) within that simulator.

    For every model that a simulator publicly exposes, the ``ModelFactory``
    provides a :class:`ModelMock` attribute that actually creates the entities.

    If you access an attribute that is not a model or if the model is not
    marked as *public*, an :exc:`~mosaik.exceptions.ScenarioError` is raised.
    """
    type: Literal['event-based', 'time-based', 'hybrid']
    models: Dict[ModelName, ModelMock]

    def __init__(self, world: World, sid: SimId, proxy: Proxy):
        self.meta = proxy.meta
        self._world = world
        self._proxy = proxy
        self._sid = sid

        if "type" not in proxy.meta:
            raise ScenarioError(
                'The simulator is missing a type specification ("time-based", '
                '"event-based" or "hybrid"). This is required starting from API '
                'version 3.'
            )
        self.type = proxy.meta["type"]
        if self.type not in ["time-based", "event-based", "hybrid"]:
            raise ScenarioError(
                f"The type '{self.type}' is not a valid type. (It should be one of"
                "'time-based', 'event-based' and 'hybrid'.) Please check for typos "
                f"in your simulator's init function and meta."
            )

        self.models = {}
        for model, props in self.meta["models"].items():
            if model in MOSAIK_METHODS:
                raise ScenarioError(
                    f"Simulator {sid} uses an illegal model name: {model}. This name "
                    "is already the name of a mosaik API method."
                )               
            self.models[model] = ModelMock(self._world, self, model, self._proxy)
            # Make public models accessible
            if props.get("public", True):
                setattr(self, model, self.models[model])

        # Bind extra_methods to this instance:
        for meth_name in self.meta["extra_methods"]:
            # We need get_wrapper() in order to avoid problems with scoping
            # of the name "meth". Without it, "meth" would be the same for all
            # wrappers.
            if meth_name in MOSAIK_METHODS:
                raise ScenarioError(
                    f"Simulator {sid} uses an illegal name for an extra method: "
                    f'"{meth_name}". This is already the name of a mosaik API method.'
                )
            if meth_name in self.models.keys():
                raise ScenarioError(
                    f"Simulator {sid} uses an illegal name for an extra method: "
                    f'"{meth_name}". This is already the name of a model of this '
                    "simulator."
                )
            def get_wrapper(connection, meth_name):
                def wrapper(*args, **kwargs):
                    return world.loop.run_until_complete(
                        connection.send([meth_name, args, kwargs])
                    )
                wrapper.__name__ = meth_name
                return wrapper

            setattr(self, meth_name, get_wrapper(proxy, meth_name))

    def __getattr__(self, name):
        # Implemented in order to improve error messages.
        models = self.meta["models"]
        if name in models:
            raise AttributeError(f'Model "{name}" is not public.')
        else:
            raise AttributeError(
                f'Model factory for "{self._sid}" has no model and no function '
                f'"{name}".'
            )


class ModelMock(object):
    """
    Instances of this class are exposed as attributes of
    :class:`ModelFactory` and allow the instantiation of simulator models.

    You can *call* an instance of this class to create exactly one entity:
    ``sim.ModelName(x=23)``. Alternatively, you can use the :meth:`create()`
    method to create multiple entities with the same set of parameters at once:
    ``sim.ModelName.create(3, x=23)``.
    """
    name: ModelName
    _world: World
    _factory: ModelFactory
    _proxy: Proxy
    params: FrozenSet[str]
    any_inputs: bool
    # TODO: Maybe introduce a "UniversalSet" abstraction to deal with
    # any_inputs in a more unified way?
    event_inputs: FrozenSet[Attr]
    measurement_inputs: FrozenSet[Attr]
    event_outputs: FrozenSet[Attr]
    measurement_outputs: FrozenSet[Attr]

    def __init__(self, world: World, factory: ModelFactory, model: ModelName, proxy: Proxy):
        self._world = world
        self._factory = factory
        self.name = model
        self._proxy = proxy
        model_desc = proxy.meta['models'][model]
        self.params = frozenset(model_desc.get('params', []))
        self.any_inputs = model_desc.get('any_inputs', False)
        attrs = frozenset(model_desc.get('attrs', []))
        if self._factory.type != "hybrid":
            for special_key in ["trigger", "non-persistent"]:
                if special_key in model_desc:
                    raise ScenarioError(
                        f'The key "{special_key}" in the model description is only '
                        f'valid for hybrid simulators, but your {self._factory.type} '
                        f'simulator {self._factory._sid} uses it in its model '
                        f'"{model}". Remove the key or turn it into a hybrid simulator.'
                    )
        for invalid_key, alternative in [
            ("non-trigger", "trigger"),
            ("persistent", "non-persistent"),
        ]:
            if invalid_key in model_desc:
                raise ScenarioError(
                    f'The key "{invalid_key}" is not supported in model '
                    f'descriptions, but your simulator {self._factory._sid} uses it '
                    f'in its model "{model}". Specify the "{alternative}" attributes, '
                    'instead.'
                )
            
        if proxy.meta['type'] == 'event-based':
            self.event_inputs = attrs
            self.measurement_inputs = frozenset()
            self.event_outputs = attrs
            self.measurement_outputs = frozenset()
        elif proxy.meta['type'] == 'time-based':
            self.event_inputs = frozenset()
            self.measurement_inputs = attrs
            self.event_outputs = frozenset()
            self.measurement_outputs = attrs
        else:
            self.event_inputs = frozenset(model_desc.get('trigger', []))
            if not self.event_inputs.issubset(attrs):
                raise ScenarioError(
                    'Attributes in "trigger" must be a subset of attributes in '
                    f'"attrs", but for model "{model}", the following attributes only '
                    f'appear in "trigger": {", ".join(self.event_inputs - attrs)}.'
                )
            self.measurement_inputs = attrs - self.event_inputs
            self.event_outputs = frozenset(model_desc.get("non-persistent", []))
            if not self.event_outputs.issubset(attrs):
                raise ScenarioError(
                    'Attributes in "non-persistent" must be a subset of attributes in '
                    f'"attrs", but for model "{model}", the following attributes only '
                    'appear in "non-persistent": '
                    f'{", ".join(self.event_outputs - attrs)}.'
                )
            self.measurement_outputs = attrs - self.event_outputs

    @property
    def input_attrs(self) -> FrozenSet[Attr]:
        return self.event_inputs | self.measurement_inputs

    @property
    def output_attrs(self) -> FrozenSet[Attr]:
        return self.event_outputs | self.measurement_outputs
    
    def __call__(self, **model_params):
        """
        Call :meth:`create()` to instantiate one model.
        """
        return self.create(1, **model_params)[0]

    def create(self, num: int, **model_params):
        """
        Create *num* entities with the specified *model_params* and return
        a list with the entity dicts.

        The returned list of entities is the same as returned by
        :meth:`mosaik_api.Simulator.create()`, but the simulator is prepended
        to every entity ID to make them globally unique.
        """
        self._check_params(**model_params)

        entities = self._world.loop.run_until_complete(
            self._proxy.send(["create", (num, self.name), model_params])
        )
        assert len(entities) == num, (
            f'{num} entities were requested but {len(entities)} were created.'
        )

        return self._make_entities(entities, assert_type=self.name)

    def _check_params(self, **model_params):
        unexpected_params = set(model_params.keys()).difference(self.params)
        if unexpected_params:
            sep = "', '"
            raise TypeError(
                "create() got unexpected keyword arguments: '"
                f"{sep.join(unexpected_params)}'"
            )

    def _make_entities(self, entity_dicts, assert_type=None):
        """
        Recursively create lists of :class:`Entity` instance from a list
        of *entity_dicts*.
        """
        sid = self._factory._sid
        entity_graph = self._world.entity_graph

        entity_set = []
        for e in entity_dicts:
            self._assert_model_type(assert_type, e)

            children = e.get('children', [])
            if children:
                children = self._make_entities(children)
            model = self._factory.models[e['type']]
            entity = Entity(sid, e['eid'], self.name, model, children)

            entity_set.append(entity)
            entity_graph.add_node(entity.full_id, sid=sid, type=e['type'])
            for rel in e.get('rel', []):
                entity_graph.add_edge(entity.full_id, FULL_ID % (sid, rel))

        return entity_set

    def _assert_model_type(self, assert_type, e):
        """
        Assert that entity *e* has entity type *assert_type* )ifs not none
 ]       or else any valid type.
        """
        if assert_type is not None:
            assert e['type'] == assert_type, (
                f'Entity "{e["eid"]}" has the wrong type: "{e["type"]}"; '
                f'"{assert_type}" required.'
            )
        else:
            assert e['type'] in self._proxy.meta['models'], (
                f'Type "{e["type"]}" of entity "{e["eid"]}" not found in sim\'s meta '
                'data.'
            )


class Entity(object):
    """
    An entity represents an instance of a simulation model within mosaik.
    """
    __slots__ = ['sid', 'eid', 'sim_name', 'model_mock', 'children', 'connection']
    sid: SimId
    """The ID of the simulator this entity belongs to."""
    eid: EntityId
    """The entity's ID."""
    sim_name: str
    """The entity's simulator name."""
    model_mock: ModelMock
    """The entity's type (or class)."""
    children: Iterable[Entity]
    """An entity set containing subordinate entities."""

    def __init__(
        self,
        sid: SimId,
        eid: EntityId,
        sim_name: str,
        model_mock: ModelMock,
        children: Iterable[Entity],
    ):
        self.sid = sid
        self.eid = eid
        self.sim_name = sim_name
        self.model_mock = model_mock
        self.children = children if children is not None else set()

    @property
    def type(self) -> ModelName:
        return self.model_mock.name

    @property
    def model(self) -> ModelName:
        return self.model_mock.name

    @property
    def full_id(self) -> FullId:
        """
        Full, globally unique entity id ``sid.eid``.
        """
        return FULL_ID % (self.sid, self.eid)

    def triggered_by(self, attr: Attr) -> bool:
        return (attr in self.model_mock.event_inputs) or (
            self.model_mock._factory.type == "event-based"
            and self.model_mock.any_inputs
        )

    def is_persistent(self, attr: Attr) -> bool:
        return (attr in self.model_mock.measurement_outputs)

    def __str__(self):
        return (
            f"{self.__class__.__name__}(model={self.model!r}, eid={self.eid!r}, "
            f"sid={self.sid!r})"
        )

    def __repr__(self):
        return (
            f"{self.__class__.__name__}(model_mock={self.model_mock!r}, "
            f"eid={self.eid!r}, sid={self.sid!r}, children={self.children!r})"
        )
