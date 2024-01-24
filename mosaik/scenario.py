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
from copy import copy
import itertools
from loguru import logger
import networkx
from tqdm import tqdm
from typing import (
    Any,
    Callable,
    Dict,
    FrozenSet,
    Iterable,
    List,
    Optional,
    Set,
    Tuple,
    Union,
)
import warnings
from typing_extensions import Literal, TypedDict

from mosaik_api_v3.connection import Channel
from mosaik_api_v3.types import Attr, CreateResult, EntityId, FullId, ModelDescription, ModelName, SimId

from mosaik import simmanager
from mosaik.dense_time import DenseTime
from mosaik.proxies import Proxy
from mosaik.simmanager import SimRunner
from mosaik import scheduler
from mosaik.exceptions import ScenarioError, SimulationError
from mosaik.in_or_out_set import OutSet, InOrOutSet, parse_set_triple, wrap_set


class MosaikConfig(TypedDict, total=False):
    addr: Tuple[str, int]
    start_timeout: float
    stop_timeout: float

class _MosaikConfigTotal(TypedDict):
    """A total version for :cls:`MosaikConfig` for internal use.
    """

    addr: Tuple[str, int]
    start_timeout: float
    stop_timeout: float

base_config: _MosaikConfigTotal = {
    'addr': ('127.0.0.1', 5555),
    'start_timeout': 10,  # seconds
    'stop_timeout': 10,  # seconds
}

FULL_ID = simmanager.FULL_ID

SENTINEL = object()
"""Sentinel for initial data call (we can't use None as the user might
want to supply that value.)
"""


class ModelOptionals(TypedDict, total=False):
    env: Dict[str, str]
    """The environment variables to set for this simulator."""
    cwd: str
    """The current working directory for this simulator."""
    api_version: str
    """The API version of the connected simulator. Set this to suppress
    warnings about this simulator being outdated.
    """


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

    sim_config: SimConfig
    config: _MosaikConfigTotal
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
    loop: asyncio.AbstractEventLoop
    incoming_connections_queue: asyncio.Queue[Channel]
    sims: Dict[SimId, simmanager.SimRunner]
    """A dictionary of already started simulators instances."""
    _sim_ids: Dict[ModelName, itertools.count[int]]

    entity_graph: networkx.Graph[FullId]

    def __init__(
        self,
        sim_config: SimConfig,
        mosaik_config: Optional[MosaikConfig] = None,
        time_resolution: float = 1.,
        debug: bool = False,
        cache: bool = True,
        max_loop_iterations: int = 100,
        asyncio_loop: Optional[asyncio.AbstractEventLoop] = None,
    ):
        self.sim_config = sim_config
        """The config dictionary that tells mosaik how to start a simulator."""

        self.config = copy(base_config)
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
        async def setup_queue() -> asyncio.Queue[Channel]:
            return asyncio.Queue()
        self.incoming_connections_queue = self.loop.run_until_complete(setup_queue())

        async def connected_cb(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
            await self.incoming_connections_queue.put(Channel(reader, writer))

        self.server = self.loop.run_until_complete(
            asyncio.start_server(
                connected_cb,
                self.config['addr'][0],
                self.config['addr'][1],
            )
        )

        self.entity_graph = networkx.Graph()
        """The :func:`graph <networkx.Graph>` of related entities. Nodes are
        ``(sid, eid)`` tuples.  Each note has an attribute *entity* with an
        :class:`Entity`."""

        self.sim_progress = 0
        """Progress of the current simulation (in percent)."""

        self._debug = False
        if debug:
            logger.warning(
                "You are running your simulation in debug mode. This can lead to "
                "significant slow-downs, as it will create a graph of the entire "
                "execution. Only use this mode if you intend to analyze the execution "
                "graph afterwards."
            )
            self._debug = True
            self.execution_graph: networkx.DiGraph[Tuple[SimId, DenseTime]] = networkx.DiGraph()

        # Contains ID counters for each simulator type.
        self._sim_ids = defaultdict(itertools.count)
        self.use_cache = cache

    def start(
        self,
        sim_name: str,
        sim_id: Optional[SimId] = None,
        **sim_params: Any,
    ) -> ModelFactory:
        """
        Start the simulator named *sim_name* and return a
        :class:`ModelFactory` for it.
        """
        if not sim_id:
            counter = self._sim_ids[sim_name]
            sim_id = '%s-%s' % (sim_name, next(counter))
        if sim_id in self.sims:
            raise ScenarioError(
                f"A simulator with sim_id '{sim_id}' has already been started. "
                "Choose a different sim_id."
            )
        logger.info(
            'Starting "{sim_name}" as "{sim_id}" ...',
            sim_name=sim_name,
            sim_id=sim_id,
        )
        proxy = self.loop.run_until_complete(
            simmanager.start(self, sim_name, sim_id, self.time_resolution, sim_params)
        )
        # Create the ModelFactory before the SimRunner as it performs
        # some checks on the simulator's meta.
        model_factory = ModelFactory(self, sim_id, proxy)
        self.sims[sim_id] = SimRunner(sim_id, proxy)
        if self.use_cache:
            self.sims[sim_id].outputs = {}
        return model_factory

    def connect_one(
        self,
        src: Entity,
        dest: Entity,
        src_attr: Attr,
        dest_attr: Optional[Attr] = None,
        time_shifted: Union[bool, int] = False,
        weak: bool = False,
        initial_data: Any = SENTINEL,
    ):
        if not dest_attr:
            dest_attr = src_attr

        src_sim = self.sims[src.sid]
        dest_sim = self.sims[dest.sid]
        
        src_port = (src.eid, src_attr)
        dest_port = (dest.eid, dest_attr)

        problems: List[str] = []
        
        if src_attr not in src.model_mock.output_attrs:
            problems.append(
                "the source attribute does not exist"
            )
        if dest_attr not in dest.model_mock.input_attrs:
            problems.append(
                "the destination attribute does not exist"
            )

        if (time_shifted or weak) and dest_attr in dest.model_mock.measurement_inputs:
            if initial_data is SENTINEL:
                problems.append(
                    "weak or time-shifted connection into non-trigger attribute "
                    "requires initial data"
                )
        elif initial_data is not SENTINEL:
            logger.warning(
                f"Gave initial data for connection from {src.full_id}.{src_attr} to "
                f"{dest.full_id}.{dest_attr} where it is not needed"
            )

        if problems:
            raise ScenarioError(
                f"The are problems connecting {src.full_id}.{src_attr} to "
                f"{dest.full_id}.{dest_attr}:\n- "
                + "\n- ".join(problems)
            )

        if (
            dest_attr in dest.model_mock.measurement_inputs
            and src_attr in src.model_mock.event_outputs
        ):
            logger.warning(
                f"A connection between the non-persistent attribute {src_attr} of "
                f"{src.sid} and the non-trigger attribute {dest_attr} of "
                f"{dest.sid} is not recommended. This might cause problems in the "
                "simulation! See also: https://mosaik.readthedocs.io/en/latest/"
                "scenario-definition.html#connecting-entities"
            )

        delay = DenseTime(time_shifted, weak)
        dest_sim.input_delays[src_sim] = min(dest_sim.input_delays.get(src_sim, delay), delay)

        is_pulled = src_sim.outputs is not None and src.is_persistent(src_attr)
        
        if src.is_persistent(src_attr) and not self.use_cache:
            dest_sim.persistent_inputs.setdefault(dest.eid, {}).setdefault(dest_attr, {}).setdefault(src.full_id, None)

        src_sim.output_request.setdefault(src.eid, []).append(src_attr)

        if is_pulled:
            dest_sim.pulled_inputs.setdefault((src_sim, time_shifted), set()).add((src_port, dest_port))
        else:
            src_sim.output_to_push.setdefault(src_port, []).append((dest_sim, time_shifted, dest_port))

        src_sim.successors.add(dest_sim)

        if dest.triggered_by(dest_attr):
            src_sim.triggers.setdefault(src_port, []).append((dest_sim, delay))

        if initial_data is not SENTINEL:
            if is_pulled:
                src_sim.outputs.setdefault(
                    -int(time_shifted), {}
                ).setdefault(src.eid, {})[src_attr] = initial_data
            else:
                dest_sim.persistent_inputs.setdefault(
                    dest.eid, {}
                ).setdefault(dest_attr, {})[src.full_id] = initial_data

        self.entity_graph.add_edge(src.full_id, dest.full_id)
    
    def connect_async_requests(self, src: ModelFactory, dest: ModelFactory):
        warnings.warn(
            "Connections with async_requests are deprecated. They and the set_data "
            "function will be removed in a future release. Use time_shifted and weak "
            "connections instead.",
            category=DeprecationWarning,
        )
        src_sim = self.sims[src._sid]
        dest_sim = self.sims[dest._sid]
        src_sim.successors.add(dest_sim)
        src_sim.successors_to_wait_for.add(dest_sim)
        # DenseTime(0) is always minimal, so we dont need to compare to
        # previous value of input_delays[src_sim]
        dest_sim.input_delays[src_sim] = DenseTime(0)  
         
    def connect(
        self,
        src: Entity,
        dest: Entity,
        *attr_pairs: Union[str, Tuple[str, str]],  # type: ignore
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
        simulator at the first step (e.g. *{'src_attr': value}*).
        """

        # Expand single attributes "attr" to ("attr", "attr") tuples:
        attr_pairs: Set[Tuple[Attr, Attr]] = set(
            (a, a) if isinstance(a, str) else a for a in attr_pairs
        )
        errors: List[ScenarioError] = []
        for src_attr, dest_attr in attr_pairs:
            try:
                self.connect_one(
                    src,
                    dest,
                    src_attr,
                    dest_attr,
                    time_shifted=time_shifted,
                    weak=weak,
                    initial_data=initial_data.get(src_attr, SENTINEL),
                )
            except ScenarioError as e:
                errors.append(e)

        if async_requests:
            self.connect_async_requests(src.model_mock._factory, dest.model_mock._factory)

        if errors:
            raise ScenarioError(
                "While connecting entities, the following errors occurred:\n - "
                + "\n - ".join(str(e) for e in errors)
            )

        trigger: Set[Tuple[EntityId, Attr]] = set()
        for src_attr, dest_attr in attr_pairs:
            if (dest.triggered_by(dest_attr)):
                trigger.add((src.eid, src_attr))

        # Add relation in entity_graph
        self.entity_graph.add_edge(src.full_id, dest.full_id)

    def set_initial_event(self, sid: SimId, time: int = 0):
        """
        Set an initial step for simulator *sid* at time *time* (default=0).
        """
        self.sims[sid].next_steps = [DenseTime(time)]

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
        """Start the simulation until the simulation time *until* is
        reached.

        Before this method returns, it stops all simulators and closes
        mosaik's server socket. So this method should only be called
        once.

        :param until: The end of the simulation in mosaik time steps
            (exclusive).

        :param rt_factor: The real-time factor. If set to a number > 0,
            the simulation will run in real-time mode. A real-time 
            factor of 1. means that 1 second in simulated time takes
            1 second in real time. An real-time factor of 0.5 will let
            the simulation run twice as fast as real time. For correct
            behavior of the real-time factor, the time resolution of the
            scenario has to be set adequately (the default is 1 second).

        :param rt_strict: If the simulators are too slow for the
            real-time factor you chose, mosaik will only print a warning
            by default. In order to raise a :exc:`RuntimeError` instead,
            you can set *rt_strict* to ``True``.

        :param print_progress: Whether progress bars are printed while
            the simulation is running. The default is to print one bar
            representing the global progress of the simulation. You can
            also set the value to ``'individual'`` to get one bar per
            simulator in your simulation (in addition to the global
            one). A value of ``False`` turns off the progress bars
            completely.
            
            The progress bars use
            `tqdm <https://pypi.org/project/tqdm/>`_; see their
            documentation on how to write to the console without
            interfering with the bars.

        :param lazy_stepping: Whether to prevent simulators from running
            ahead of their successors by more than one step. If
            ``False`` a simulator always steps as long all input is
            provided. This might decrease the simulation time but
            increase the memory consumption.
        """
        if hasattr(self, "until"):
            raise RuntimeError(
                "Simulation has already been run and can only be run once for a World "
                "instance."
            )

        # Check if a simulator is not connected to anything:
        # TODO: Rebuild this test without df_graph (or maybe check for
        # connectedness instead).

        # Creating the topological ranking will ensure that there are no
        # cycles in the dataflow graph that are not resolved using
        # time-shifted or weak connections.
        self.ensure_no_dataflow_cycles()

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

    def cache_triggering_ancestors(self):
        """
        Collects the ancestors of each simulator and stores them in the
        respective simulator object.
        """
        trigger_graph: networkx.DiGraph[SimRunner] = networkx.DiGraph()
        for src_sim in self.sims.values():
            for successors in src_sim.triggers.values():
                for (dest_sim, delay) in successors:
                    min_delay = delay
                    if trigger_graph.has_edge(src_sim, dest_sim):
                        min_delay = min(delay, trigger_graph[src_sim][dest_sim]["delay"])
                    trigger_graph.add_edge(src_sim, dest_sim, delay=min_delay)
        for dest_sim in trigger_graph.nodes:
            for src_sim in networkx.ancestors(trigger_graph, dest_sim):
                distance = networkx.shortest_path_length(trigger_graph, src_sim, dest_sim, weight="delay")
                dest_sim.triggering_ancestors.append((src_sim, distance))

    def ensure_no_dataflow_cycles(self):
        """
        Deduce a simulator ranking from a topological sort of the df_graph.
        """
        immediate_graph: networkx.DiGraph[SimRunner] = networkx.DiGraph()
        for sim in self.sims.values():
            for pred_sim, delay in sim.input_delays.items():
                if delay == DenseTime(0):
                    immediate_graph.add_edge(pred_sim, sim)
        # If there are performance problems, it might be faster to first try sorting
        # this graph topologically. If that succeeds, there will be no cycles, so the
        # cycles computation can be skipped.
        for cycle in networkx.simple_cycles(immediate_graph):
            # If we run into any cycles, we raise, thus not computing all cycles.
            raise ScenarioError(
                "Your scenario contains cycles that are not broken up using "
                "time-shifted or weak connections. mosaik is unable to determine which "
                "simulator to run first in these cases. Here is an example of one such "
                f"cycle: {cycle}."
            )

    def shutdown(self):
        """
        Shut-down all simulators and close the server socket.
        """
        if self.server.is_serving():
            self.server.close()

        if not self.loop.is_closed():
            for sim in self.sims.values():
                self.loop.run_until_complete(sim.stop())
            self.loop.close()


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
        for meth_name in self.meta.get("extra_methods", []):
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
            def get_wrapper(connection: Proxy, meth_name: str) -> Callable[..., Any]:
                def wrapper(*args: Any, **kwargs: Any):
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


def parse_attrs(
    model_desc: ModelDescription,
    type: Literal['time-based', 'event-based', 'hybrid']
) -> Tuple[InOrOutSet[Attr], InOrOutSet[Attr], InOrOutSet[Attr], InOrOutSet[Attr]]:
    """Parse the attrs and their trigger/persistent state.

    The guiding principle is this: The user can specify as little
    information as possible and the rest will be inferred, but
    inconsistent information will lead to an error.

    If attrs, trigger and non-trigger are all given, trigger and
    non-trigger must form a partition of attrs. If only two are given,
    the third in inferred, provided this can be done in such a way that
    trigger and non-trigger form a partition of attrs. If
    any_inputs=True, the set of all possible attrs is used instead of
    the ones specified in attrs. If only attrs is given, a default
    is chosen for the others, based on the type of the simulator.

    The same applieds to attrs, persistent and non-persistent, except
    that any_inputs is not considered (as these are outputs).

    :param model_desc: The `ModelDescription` to parse
    :param type: The simulator's type (for setting default attribute
        types).
    :return: A four-tuple of :class:`InOrOutSet`, giving the
        measurement inputs, event inputs, measurement outputs, and event
        outputs.        
    :raises ValueError: if the information is insufficient or
        inconsistent
    """
    error_template = (
            "%s simulators may not specify %s attrs (use a hybrid simulator, instead, "
            "if you need both types of %s attributes), and they must list all their "
            "attrs as %s if that key is present"
    )
    
    if model_desc.get('any_inputs', False):
        inputs: Optional[InOrOutSet[Attr]] = OutSet()
    else:
        inputs = wrap_set(model_desc.get('attrs'))
    empty: FrozenSet[Attr] = frozenset()
    default_measurements = empty if type == 'event-based' else None
    measurement_inputs = wrap_set(model_desc.get('non-trigger', default_measurements))
    default_events = None if type == 'event-based' else empty
    event_inputs = wrap_set(model_desc.get('trigger', default_events))
    measurement_inputs, event_inputs = parse_set_triple(
        inputs, measurement_inputs, event_inputs,
        "attrs", "non-trigger", "trigger"
    )
    if type == 'time-based' and event_inputs != frozenset():
        raise ValueError(
            error_template % ("time-based", "trigger", "input", "non-trigger")
        )
    if type == 'event-based' and measurement_inputs != frozenset():
        raise ValueError(
            error_template % ("event-based", "non-trigger", "inpus", "trigger")
        )
    
    outputs = wrap_set(model_desc.get('attrs'))
    default_measurements = empty if type == 'event-based' else None
    measurement_outputs = wrap_set(model_desc.get('persistent', default_measurements))
    default_events = None if type == 'event-based' else empty
    event_outputs = wrap_set(model_desc.get('non-persistent', default_events))
    measurement_outputs, event_outputs = parse_set_triple(
        outputs, measurement_outputs, event_outputs,
        "attrs", "persistent", "non-persistent"
    )
    if type == 'time-based' and event_outputs != frozenset():
        raise ValueError(
            error_template % ("time-based", "non-persistent", "output", "persistent")
        )
    if type == 'event-based' and measurement_outputs != frozenset():
        raise ValueError(
            error_template % ("event-based", "persistent", "output", "non-persistent")
        )

    return measurement_inputs, event_inputs, measurement_outputs, event_outputs


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
    event_inputs: InOrOutSet[Attr]
    measurement_inputs: InOrOutSet[Attr]
    event_outputs: InOrOutSet[Attr]
    measurement_outputs: InOrOutSet[Attr]

    def __init__(
        self,
        world: World,
        factory: ModelFactory,
        model: ModelName,
        proxy: Proxy,
    ):
        self._world = world
        self._factory = factory
        self.name = model
        self._proxy = proxy
        model_desc = proxy.meta['models'][model]
        self.params = frozenset(model_desc.get('params', []))

        (
            self.measurement_inputs,
            self.event_inputs,
            self.measurement_outputs,
            self.event_outputs,
        ) = parse_attrs(model_desc, self._factory.type)

    @property
    def input_attrs(self) -> InOrOutSet[Attr]:
        return self.event_inputs | self.measurement_inputs

    @property
    def output_attrs(self) -> InOrOutSet[Attr]:
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
        :meth:`mosaik_api_v3.Simulator.create()`, but the simulator is prepended
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

    def _make_entities(
        self, entity_dicts: List[CreateResult], assert_type: Optional[ModelName] = None
    ) -> List[Entity]:
        """
        Recursively create lists of :class:`Entity` instance from a list
        of *entity_dicts*.
        """
        sid = self._factory._sid
        entity_graph = self._world.entity_graph

        entity_set: List[Entity] = []
        for e in entity_dicts:
            self._assert_model_type(assert_type, e)

            children = e.get('children')
            if children is not None:
                children = self._make_entities(children)
            model = self._factory.models[e['type']]
            entity = Entity(
                sid, e['eid'], self.name, model, children, e.get("extra_info")
            )

            entity_set.append(entity)
            entity_graph.add_node(entity.full_id, sid=sid, type=e['type'])
            for rel in e.get('rel', []):
                entity_graph.add_edge(entity.full_id, FULL_ID % (sid, rel))

        return entity_set

    def _assert_model_type(
        self, assert_type: Optional[ModelName], e: CreateResult
    ) -> None:
        """Assert that entity ``e`` has entity type ``assert_type``, or
        any valid model type of the simulator if ``assert_type`` is
        ``None``.
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
    __slots__ = ['sid', 'eid', 'sim_name', 'model_mock', 'children', 'extra_info']
    sid: SimId
    """The ID of the simulator this entity belongs to."""
    eid: EntityId
    """The entity's ID."""
    sim_name: str
    """The entity's simulator name."""
    model_mock: ModelMock
    """The entity's type (or class)."""
    children: List[Entity]
    """An entity set containing subordinate entities."""
    extra_info: Any

    def __init__(
        self,
        sid: SimId,
        eid: EntityId,
        sim_name: str,
        model_mock: ModelMock,
        children: Optional[Iterable[Entity]],
        extra_info: Any = None,
    ):
        self.sid = sid
        self.eid = eid
        self.sim_name = sim_name
        self.model_mock = model_mock
        self.children = list(children) if children is not None else []
        self.extra_info = extra_info

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
        return attr in self.model_mock.event_inputs

    def is_persistent(self, attr: Attr) -> bool:
        return attr in self.model_mock.measurement_outputs

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
