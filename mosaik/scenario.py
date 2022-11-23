"""
This module provides the interface for users to create simulation scenarios for
mosaik.

The :class:`World` holds all necessary data for the simulation and allows the
user to start simulators. It provides a :class:`ModelFactory` (and
a :class:`ModelMock`) via which the user can instantiate model instances
(*entities*). The method :meth:`World.run()` finally starts the simulation.
"""
from __future__ import annotations

from collections import defaultdict
import itertools

import networkx
from simpy.core import Environment
from loguru import logger
from tqdm import tqdm

from mosaik import simmanager
from mosaik import scheduler
from mosaik import util
from mosaik.exceptions import ScenarioError, SimulationError

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from typing import Any, Dict, Iterable, List, Literal, Optional, Tuple, TypedDict, Union
    from simpy.events import Event


backend = simmanager.backend
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
    class DataflowEgdeEvents(TypedDict, total=False):
        wait_event: Event
        """Event on which destination simulator is waiting for its inputs."""
        wait_lazy: Event
        """Event on which source simulator is waiting in case of lazy stepping."""
        wait_async: Event
        """Event on which source simulator is waiting to support async requests."""
        

    class DataflowEdge(DataflowEgdeEvents):
        """The information associated with an edge in the dataflow graph."""
        async_requests: bool
        """Whether there can be async requests along this edge."""
        time_shifted: bool
        """Whether dataflow along this edge is time shifted."""
        weak: bool
        """Whether this edge is weak (used for same-time loops)."""
        trigger: bool
        """Whether any of the destination simulator's inputs used by this edge are
        trigger inputs."""
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
    env: Environment
    """The SimPy environment for this simulation."""
    sims: Dict[SimId, simmanager.SimProxy]
    """A dictionary of already started simulators instances."""

    def __init__(
        self,
        sim_config: SimConfig,
        mosaik_config=None,
        time_resolution: float = 1.,
        debug: bool = False,
        cache: bool = True,
        max_loop_iterations: int = 100
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

        self.env = backend.Environment()  # type: ignore
        """The SimPy.io networking :class:`~simpy.io.select.Environment`."""

        self.srv_sock = backend.TCPSocket.server(self.env, self.config['addr'])
        """Mosaik's server socket."""

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
        logger.info('Starting "{sim_name}" as "{sim_id}" ...'
                   , sim_name=sim_name, sim_id=sim_id)
        sim = simmanager.start(self, sim_name, sim_id, self.time_resolution,
                               sim_params)
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
            logger.warning('DEPRECATION: Async_request connections are deprecated'
                           'and will be removed with set_data() in future releases.'
                           'Use time_shifted and weak connections instead')

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

        self.df_graph.add_edge(src.sid, dest.sid,
                               async_requests=async_requests,
                               time_shifted=time_shifted,
                               weak=weak,
                               trigger=trigger,
                               pred_waiting=pred_waiting)

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

    def get_data(self,
        entity_set: Iterable[Entity],
        *attributes: Attr
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

        def request_data():
            requests = {self.sims[sid].proxy.get_data(outputs): sid
                        for sid, outputs in outputs_by_sim.items()}
            try:
                results = yield self.env.all_of(requests)
            except ConnectionError as e:
                msg = ('Simulator "%s" closed its connection while executing '
                       '"World.get_data()".')
                # Try to find the simulator that closed its connection
                for req, sid in requests.items():
                    if req.triggered and not req.ok:
                        raise SimulationError(msg % sid, e) from None
                else:
                    raise RuntimeError('Could not determine which simulator '
                                       'closed its connection.')

            results_by_sim = {}
            for request, value in results.items():
                sid = requests[request]
                results_by_sim[sid] = value

            return results_by_sim

        results_by_sim = util.sync_process(request_data(), self)
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
        if self.srv_sock is None:
            raise RuntimeError('Simulation has already been run and can only '
                               'be run once for a World instance.')

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
                else "Total:%s {percentage:3.0f}%% |{bar}| %s{elapsed}<{remaining}" %
                    (" " * (max_sim_id_len - 11), "  " * until_len)
            ),
            unit='steps',
        )
        for sid, sim in self.sims.items():
            sim.tqdm = tqdm(
                total=until,
                desc=sid,
                bar_format="{desc:>%i} |{bar}| {n_fmt:>%i}/{total_fmt}{postfix:10}" %
                    (max_sim_id_len, until_len),
                leave=False,
                disable=print_progress != 'individual',
            )
        import mosaik._debug as dbg  # always import, enable when requested
        if self._debug:
            dbg.enable()
        success = False
        try:
            util.sync_process(scheduler.run(self, until, rt_factor, rt_strict,
                                            lazy_stepping),
                              self)
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
        cycles = list(networkx.simple_cycles(self.df_graph))
        for cycle in cycles:
            sim_pairs = list(zip(cycle, cycle[1:] + [cycle[0]]))
            loop_breaker = [self.df_graph[src_id][dest_id]['weak'] or
                            self.df_graph[src_id][dest_id]['time_shifted'] for
                            src_id, dest_id in sim_pairs]
            if not any(loop_breaker):
                raise ScenarioError('Scenario has unresolved cyclic '
                                    f'dependencies: {sorted(cycle)}. Use options '
                                    '"time-shifted" or "weak" for resolution.')
            is_weak = [self.df_graph[src_id][dest_id]['weak']
                       for src_id, dest_id in sim_pairs]
            if sum(is_weak) > 1:
                raise ScenarioError('Maximum one weak connection is allowed in'
                                    ' an elementary cycle, but there are '
                                    f'actually {sum(is_weak)} in '
                                    f'{sorted(cycle)}.')

    def cache_trigger_cycles(self):
        cycles = list(networkx.simple_cycles(self.trigger_graph))
        for sim in self.sims.values():
            for cycle in cycles:
                if sim.sid in cycle:
                    edge_ids = list(zip(cycle, cycle[1:] + [cycle[0]]))
                    cycle_edges = [self.df_graph.get_edge_data(src_id, dest_id)
                                   for src_id, dest_id in edge_ids]
                    trigger_cycle = {'sids': sorted(cycle)}
                    min_cycle_length = sum(
                        [edge['time_shifted'] for edge in cycle_edges])
                    trigger_cycle['min_length'] = min_cycle_length
                    ind_sim = cycle.index(sim.sid)
                    out_edge = cycle_edges[ind_sim]
                    suc_sid = edge_ids[ind_sim][1]
                    activators = []
                    for src_eid, dest_eid, attrs in out_edge['dataflows']:
                        dest_model = \
                            networkx.get_node_attributes(self.entity_graph,
                                                         'type')[
                                FULL_ID % (suc_sid, dest_eid)]
                        dest_trigger = \
                        self.sims[suc_sid].meta['models'][dest_model][
                            'trigger']
                        for src_attr, dest_attr in attrs:
                            if dest_attr in dest_trigger:
                                activators.append((src_eid, src_attr))
                    trigger_cycle['activators'] = activators
                    in_edge = (cycle_edges[ind_sim - 1] if ind_sim != 0
                               else cycle_edges[-1])
                    trigger_cycle['in_edge'] = in_edge
                    in_edge['loop_closing'] = True
                    trigger_cycle['time'] = -1
                    trigger_cycle['count'] = 0
                    sim.trigger_cycles.append(trigger_cycle)

    def cache_dependencies(self):
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
        all_sims = self.sims.values()
        for sim in all_sims:
            sim.related_sims = [isim for isim in all_sims if isim != sim]

    def cache_triggering_ancestors(self):
        for sim in self.sims.values():
            triggering_ancestors = sim.triggering_ancestors = []
            ancestors = list(networkx.ancestors(self.trigger_graph, sim.sid))
            for anc_sid in ancestors:
                paths = networkx.all_simple_edge_paths(self.trigger_graph,
                                                       anc_sid, sim.sid)
                distances = []
                for edges in paths:
                    distance = 0
                    for edge in edges:
                        edge = self.df_graph[edge[0]][edge[1]]
                        distance += edge['time_shifted'] or edge['weak']
                    distances.append(distance)
                distance = min(distances)
                triggering_ancestors.append((anc_sid, not distance))

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
        for sim in self.sims.values():
            util.sync_process(sim.stop(), self, ignore_errors=True)

        if self.srv_sock is not None:
            self.srv_sock.close()
            self.srv_sock = None

    def _check_attributes(self,
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
        entities = [src, dest]
        emeta = [e.sim.meta['models'][e.type] for e in entities]
        any_inputs = [False, emeta[1]['any_inputs']]
        attr_errors = []
        for attr_pair in attr_pairs:
            for i, attr in enumerate(attr_pair):
                if not (any_inputs[i] or attr in emeta[i]['attrs']):
                    attr_errors.append((entities[i], attr))
        return attr_errors

    def _check_attributes_values(self,
        src:Entity,
        dest:Entity,
        attr_pairs:Iterable[Tuple[Attr, Attr]],
    ):
        """
        Check if *src* and *dest* attributes in *attr_pairs* are a combination of
        persistent and trigger or non-persistent and non-trigger.

        """
        entities = [src, dest]
        emeta = [e.sim.meta['models'][e.type] for e in entities]
        non_persistent = set(emeta[0]['attrs']).difference(emeta[0]['persistent'])
        non_trigger = set(emeta[1]['attrs']).difference(emeta[1]['trigger'])
        for attr_pair in attr_pairs:
            if (attr_pair[1] in emeta[1]['trigger']) and (attr_pair[0] in emeta[0]['persistent']):
                logger.warning('A connection between persistent and trigger attributes is not recommended.'
                               'This might cause problems in the simulation!')
            elif (attr_pair[1] in non_trigger) and (attr_pair[0] in non_persistent):
                logger.warning('A connection between non-persistent and non-trigger attributes is not recommended. '
                               'This might cause problems in the simulation!')

    def _classify_connections_with_cache(self,
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
        entities = [src, dest]
        emeta = [e.sim.meta['models'][e.type] for e in entities]
        any_inputs = [False, emeta[1]['any_inputs']]
        any_trigger = False
        cached = []
        time_buffered = []
        memorized = []
        persistent = []

        for attr_pair in attr_pairs:
            trigger = (attr_pair[1] in emeta[1]['trigger'] or (
                any_inputs[1] and dest.sim.meta['type'] == 'event-based'))
            if trigger:
                any_trigger = True

            is_persistent = attr_pair[0] in emeta[0]['persistent']
            if is_persistent:
                persistent.append(attr_pair)
            if src.sim.meta['type'] != 'time-based':
                time_buffered.append(attr_pair)
                if is_persistent:
                    memorized.append(attr_pair)
            else:
                cached.append(attr_pair)
        return (any_trigger, tuple(cached), tuple(time_buffered),
                tuple(memorized), tuple(persistent))

    def _classify_connections_without_cache(self,
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
        entities = [src, dest]
        emeta = [e.sim.meta['models'][e.type] for e in entities]
        any_inputs = [False, emeta[1]['any_inputs']]
        trigger = False
        persistent = []
        for attr_pair in attr_pairs:
            if (attr_pair[1] in emeta[1]['trigger'] or (
                    any_inputs[1] and dest.sim.meta['type'] == 'event-based')):
                trigger = True
            is_persistent = attr_pair[0] in emeta[0]['persistent']
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

    def __init__(self, world: World, sim: simmanager.SimProxy):
        self.meta = sim.meta
        self._world = world
        self._env = world.env
        self._sim = sim

        # Create a ModelMock for every public model
        for model, props in self.meta['models'].items():
            if props['public']:
                setattr(self, model, ModelMock(self._world, model, self._sim))

        # Bind extra_methods to this instance:
        for meth in self.meta['extra_methods']:
            # We need get_wrapper() in order to avoid problems with scoping
            # of the name "meth". Without it, "meth" would be the same for all
            # wrappers.
            def get_wrapper(sim, meth):
                def wrapper(*args, **kwargs):
                    return util.sync_call(sim, meth, args, kwargs)
                wrapper.__name__ = meth
                return wrapper

            setattr(self, meth, get_wrapper(sim, meth))

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

    def __init__(self, world: World, name: str, sim: simmanager.SimProxy):
        self._world = world
        self._env = world.env
        self._name = name
        self._sim = sim
        self._sim_id = sim.sid
        self._params = sim.meta['models'][name]['params']

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
        :meth:`mosaik_api.Simulator.create()`, but the simulator is prepended
        to every entity ID to make them globally unique.
        """
        self._check_params(**model_params)

        entities = util.sync_call(self._sim, 'create', [num, self._name],
                                  model_params)
        assert len(entities) == num, (
                '%d entities were requested but %d were created.' %
                (num, len(entities)))

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
                    'Entity "%s" has the wrong type: "%s"; "%s" required.' %
                    (e['eid'], e['type'], assert_type))
        else:
            assert e['type'] in self._sim.meta['models'], (
                    'Type "%s" of entity "%s" not found in sim\'s meta data.' %
                    (e['type'], e['eid']))


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
    sim: simmanager.SimProxy

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

    def __str__(self):
        return '%s(%s)' % (self.__class__.__name__, ', '.join([
            repr(self.sid), repr(self.eid), repr(self.sim_name), self.type]))

    def __repr__(self):
        return '%s(%s)' % (self.__class__.__name__, ', '.join([
            repr(self.sid), repr(self.eid), repr(self.sim_name), self.type,
            repr(self.children), repr(self.sim)]))
