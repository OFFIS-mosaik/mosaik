"""
This module provides the async interface for users to create simulation
scenarios for mosaik. For a version that handles the asynchronicity
itself (but cannot be used within an existing event loop), see
:py:mod:`mosaik.scenario`.

The :class:`AsyncWorld` holds all necessary data for the simulation and
allows the user to start simulators. It provides a
:class:`AsyncModelFactory` (and a :class:`AsyncModelMock`) via which the
user can instantiate model instances (*entities*). The method
:meth:`AsyncWorld.run` finally starts the simulation.
"""

from __future__ import annotations

import asyncio
import contextlib
import itertools
import warnings
from collections import defaultdict
from copy import copy
from dataclasses import dataclass
from types import TracebackType
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    FrozenSet,
    Iterable,
    Iterator,
    List,
    NoReturn,
    Optional,
    Set,
    Tuple,
    Type,
    TypeVar,
    Union,
)

import networkx
from loguru import logger
from mosaik_api_v3 import OutputData
from mosaik_api_v3.connection import RemoteException
from mosaik_api_v3.types import (
    Attr,
    CreateResult,
    EntityId,
    FullId,
    ModelDescription,
    ModelName,
    OutputRequest,
    SimId,
)
from networkx import DiGraph
from tqdm import tqdm
from typing_extensions import Literal, Self, TypeAlias, TypedDict

from mosaik import scheduler, simmanager
from mosaik.exceptions import DuplicateEntityIdError, ScenarioError, SimulationError
from mosaik.greetings_util import print_greetings
from mosaik.in_or_out_set import InOrOutSet, OutSet, parse_set_triple, wrap_set
from mosaik.internal_util import doc_link
from mosaik.progress import ProgressProxy
from mosaik.proxies import Proxy
from mosaik.simmanager import (
    MosaikConfigTotal,
    PullDescription,
    PushDescription,
    SimRunner,
)
from mosaik.tiered_time import MinimalDurations, TieredDuration, TieredTime

if TYPE_CHECKING:
    from _typeshed import SupportsRichComparison


class MosaikConfig(TypedDict, total=False):
    addr: Tuple[str, int | None]
    start_timeout: float
    stop_timeout: float


class _MosaikConfigTotal(TypedDict):
    """A total version for :cls:`MosaikConfig` for internal use."""

    addr: Tuple[str, int | None]
    start_timeout: float
    stop_timeout: float


base_config: _MosaikConfigTotal = {
    "addr": ("127.0.0.1", None),
    "start_timeout": 10,  # seconds
    "stop_timeout": 10,  # seconds
}


SENTINEL = object()
"""Sentinel for initial data call (we can't  use None as the user might
want to supply that value.)

:meta private:
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
    posix: bool
    """Whether to split the given shell command using POSIX rules.
    (Default: ``False`` on Windows, ``True`` otherwise.)
    """
    auto_terminate: bool
    """Whether to terminate this process automatically at the end of the
    simulation. (Default ``true``.)
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
    """The command to start this simulator. String %(python)s will be
    replaced by the python command used to start this scenario, %(addr)s
    will be replaced by the `host:port` combination to which the
    simulator should connect."""


SimConfig: TypeAlias = Dict[str, Union[PythonModel, ConnectModel, CmdModel]]
"""Description of all the simulators you intend to use in your
simulation.
"""


@dataclass
class SimGroup:
    parent: SimGroup | None
    name: str | None

    @property
    def depth(self) -> int:
        if not self.parent:
            return 1
        return self.parent.depth + 1


def group_path(src: SimGroup, dest: SimGroup) -> Tuple[int, int, SimGroup]:
    src_groups = [src]
    while src.parent:
        src = src.parent
        src_groups.append(src)

    descent = 0
    while True:
        try:
            ascent = src_groups.index(dest)
            return (ascent, descent, dest)
        except ValueError:
            if not dest.parent:
                raise ValueError("no joint parent")
            dest = dest.parent
            descent += 1


def connect_interval(
    src_group: SimGroup, dest_group: SimGroup, time_shifted: int = 0, weak: int = 0
):
    """Given two `SimGroup`s, calculate a TieredInterval connecting
    simulators in these groups. The tiers will be 0, unless
    `time_shifted` or `weak` are specified, in which case the given
    values are placed in the highest and lowest tier, respectively.
    """
    ascent, _, common_group = group_path(src_group, dest_group)

    pre_length = src_group.depth
    cutoff = pre_length - ascent
    list_tiers = [0] * dest_group.depth
    if weak and not common_group.parent:
        raise ScenarioError(
            "Weak connections may only be used in groups. This is new in mosaik 3.3. "
            "For more information, see "
            f"{doc_link('scenario-definition', 'weak-connections')}."
        )
    if time_shifted:
        list_tiers[0] = time_shifted
    if weak:
        assert cutoff >= 2
        list_tiers[cutoff - 1] = weak
    return TieredDuration(*list_tiers, cutoff=cutoff, pre_length=pre_length)


class AsyncWorld:
    """
    The world holds all data required to specify and run the scenario.

    It provides a method to start a simulator process (:meth:`start`)
    and manages the simulator instances.

    You have to provide a ``sim_config`` which tells the world which
    simulators are available and how to start them. This will be stored
    as :attr:`sim_config`; see there for details.

    *mosaik_config* can be a dict or list of key-value pairs to set
    additional parameters overriding the defaults::

        {
            'addr': ('127.0.0.1', 5555),
            'start_timeout': 2,  # seconds
            'stop_timeout': 2,   # seconds
        }

    Here, *addr* is the network address that mosaik will bind its socket
    to. *start_timeout* and *stop_timeout* specifiy a timeout (in
    seconds) for starting/stopping external simulator processes.

    If *execution_graph* is set to ``True``, an execution graph will be
    created during the simulation. This may be useful for debugging and
    testing. Note that this increases the memory consumption and
    simulation time.

    We recommend that you use ``AsyncWorld`` in an ``async with`` block
    like so::

        async with AsyncWorld(SIM_CONFIG) as world:
            # call setup methods on world
            ...
            await world.run(UNTIL)

    This will ensure that the connections to all remote simulators are
    properly closed at the end of the simulation. Alternatively, you can
    use the :meth:`shutdown` method manually.
    """

    sim_config: SimConfig
    """The config dictionary that tells mosaik how to start a simulator.

    The sim config is a dictionary with one entry for every simulator.
    The entry itself tells mosaik how to start the simulator::

        {
            'ExampleSimA': {
                'python': 'example_sim.mosaik:ExampleSim',
            },
            'ExampleSimB': {
                'cmd': 'example_sim %(addr)s',
                'cwd': '.',
            },
            'ExampleSimC': {
                'connect': 'host:port',
            },
        }

    *ExampleSimA* is a pure Python simulator. Mosaik will import the
    module ``example_sim.mosaik`` and instantiate the class
    ``ExampleSim`` to start the simulator.

    *ExampleSimB* would be started by executing the command
    *example_sim* and passing the network address of mosaik das command
    line argument. You can optionally specify a *current working
    directory*. It defaults to ``.``.

    *ExampleSimC* can not be started by mosaik, so mosaik tries to
    connect to it.
    """
    config: MosaikConfigTotal
    """The config dictionary for general mosaik settings."""
    until: int  # type: ignore  # set in run
    """The time until which this simulation will run."""
    rt_factor: Optional[float]  # type: ignore  # set in run
    """The number of real-time seconds corresponding to one mosaik step.
    """

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
    sims: Dict[SimId, simmanager.SimRunner]
    """A dictionary of already started simulators instances."""
    _sim_ids: Dict[ModelName, Iterator[int]]

    main_group: SimGroup
    current_group: SimGroup

    entity_graph: networkx.Graph[FullId]
    """The :class:`graph <networkx.Graph>` of related entities.
    Nodes are ``(sid, eid)`` tuples. Each note has an attribute
    *entity* with an :class:`Entity`.
    """

    tqdm: tqdm[NoReturn]  # type: ignore  # set in run
    """The tqdm progress bar for the total progress."""

    default_transform_callable = Callable[[Any], Any]

    running: asyncio.Event

    def __init__(
        self,
        sim_config: SimConfig,
        mosaik_config: Optional[MosaikConfig] = None,
        time_resolution: float = 1.0,
        debug: bool = False,
        cache: bool = True,
        max_loop_iterations: int = 100,
        configure_logging: bool = False,
        skip_greetings: bool = True,
    ):
        if configure_logging:
            logger.enable("mosaik")

            # Redirect warnings to the logging system instead of
            # sys.stderr
            def user_warning(message, category, filename, lineno, file=None, line=None):
                logger.warning(f"{filename}:{lineno}: {category.__name__}: {message}")

            warnings.showwarning = user_warning

        self.default_transform_callable: Callable[[Any], Any] = lambda x: x

        if not skip_greetings:
            print_greetings()
        self.sim_config = sim_config

        self.config = copy(base_config)
        if mosaik_config:
            self.config.update(mosaik_config)

        self.sims = {}
        self.main_group = SimGroup(parent=None, name="main")
        self.current_group = self.main_group

        self.time_resolution = time_resolution
        self.max_loop_iterations = max_loop_iterations

        self.entity_graph = networkx.Graph()

        self.sim_progress = 0.0
        self.running = asyncio.Event()  # Initially unset (simulation starts paused)
        self.running.set()  # Start unpaused
        self._debug = False
        if debug:
            logger.warning(
                "You are running your simulation in debug mode. This can lead to "
                "significant slow-downs, as it will create a graph of the entire "
                "execution. Only use this mode if you intend to analyze the execution "
                "graph afterwards."
            )
            self._debug = True
            self.execution_graph: DiGraph[Tuple[SimId, TieredTime]] = DiGraph()

        # Contains ID counters for each simulator type.
        self._sim_ids = defaultdict(itertools.count)
        self.use_cache = cache

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self, exc_type: Type[Exception], exc: Exception, tb: TracebackType
    ):
        await self.shutdown()
        # Don't suppress exceptions. Later on, we might want to add
        # handling of mosaik exceptions here.
        return False

    @contextlib.contextmanager
    def group(self, group_name: str | None = None):
        parent_group = self.current_group
        new_group = SimGroup(parent=parent_group, name=group_name)
        self.current_group = new_group
        yield
        self.current_group = parent_group

    async def start(
        self,
        sim_name: str,
        sim_id: Optional[SimId] = None,
        **sim_params: Any,
    ) -> AsyncModelFactory:
        """
        Start the simulator named *sim_name* and return a
        :class:`ModelFactory` for it.
        """
        if not sim_id:
            counter = self._sim_ids[sim_name]
            sim_id = "%s-%s" % (sim_name, next(counter))
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
        proxy = await simmanager.start(
            self, sim_name, sim_id, self.time_resolution, sim_params
        )
        # Create the ModelFactory before the SimRunner as it performs
        # some checks on the simulator's meta.
        model_factory = AsyncModelFactory(self, self.current_group, sim_id, proxy)
        self.sims[sim_id] = SimRunner(
            sim_id,
            proxy,
            check_outputs=model_factory.validate_output_dict,
            depth=self.current_group.depth,
        )
        if self.use_cache:
            self.sims[sim_id].outputs = {}
        return model_factory

    def connect_one(  # noqa: C901
        self,
        src: Entity,
        dest: Entity,
        src_attr: Attr,
        dest_attr: Optional[Attr] = None,
        time_shifted: Union[bool, int] = False,
        weak: bool = False,
        initial_data: Any = SENTINEL,
        transform: Callable[[Any], Any] = default_transform_callable,
    ):
        if not dest_attr:
            dest_attr = src_attr

        src_sim = self.sims[src.sid]
        dest_sim = self.sims[dest.sid]

        src_port = (src.eid, src_attr)
        dest_port = (dest.eid, dest_attr)

        problems: List[str] = []

        if src_attr not in src.model_mock.output_attrs:
            problems.append("the source attribute does not exist")
        if dest_attr not in dest.model_mock.input_attrs:
            problems.append("the destination attribute does not exist")

        if (time_shifted or weak) and dest_attr in dest.model_mock.measurement_inputs:
            if initial_data is SENTINEL:
                problems.append(
                    "weak or time-shifted connection into non-trigger attribute "
                    "requires initial data"
                )
        elif initial_data is not SENTINEL:
            warnings.warn(
                f"Gave initial data for connection from {src.full_id}.{src_attr} to "
                f"{dest.full_id}.{dest_attr} where it is not needed"
            )

        if problems:
            raise ScenarioError(
                f"There are problems connecting {src.full_id}.{src_attr} to "
                f"{dest.full_id}.{dest_attr}:\n- " + "\n- ".join(problems)
            )

        if (
            dest_attr in dest.model_mock.measurement_inputs
            and src_attr in src.model_mock.event_outputs
        ):
            warnings.warn(
                f"A connection between the non-persistent attribute {src_attr} of "
                f"{src.sid} and the non-trigger attribute {dest_attr} of "
                f"{dest.sid} is not recommended. This might cause problems in the "
                "simulation! See also: https://mosaik.readthedocs.io/en/latest/"
                "scenario-definition.html#connecting-entities"
            )

        src_group = src.model_mock._factory._group
        dest_group = dest.model_mock._factory._group
        delay = connect_interval(src_group, dest_group, int(time_shifted), int(weak))

        dest_sim.input_delays.setdefault(src_sim, MinimalDurations()).insert(delay)

        is_pulled = src_sim.outputs is not None and src.is_persistent(src_attr)

        if src.is_persistent(src_attr) and not self.use_cache:
            dest_sim.persistent_inputs.setdefault(dest.eid, {}).setdefault(
                dest_attr, {}
            ).setdefault(src.full_id, None)

        src_sim.output_request.setdefault(src.eid, []).append(src_attr)

        if is_pulled:
            output_entry = dest_sim.pulled_inputs.setdefault((src_sim, delay), [])
            output_entry.append(
                PullDescription(
                    src_port=src_port, dest_port=dest_port, transform=transform
                )
            )

        else:
            output_entry = src_sim.output_to_push.setdefault(
                src_port,
                [],
            )
            output_entry.append(
                PushDescription(
                    dest_sim=dest_sim,
                    delay=delay,
                    dest_port=dest_port,
                    transform=transform,
                )
            )

        src_sim.successors[dest_sim] = connect_interval(src_group, dest_group)

        if dest.triggered_by(dest_attr):
            src_sim.triggers.setdefault(src_port, []).append((dest_sim, delay))

        if initial_data is not SENTINEL:
            if is_pulled:
                assert src_sim.outputs is not None
                src_sim.outputs.setdefault(-int(time_shifted), {}).setdefault(
                    src.eid, {}
                )[src_attr] = initial_data
            else:
                dest_sim.persistent_inputs.setdefault(dest.eid, {}).setdefault(
                    dest_attr, {}
                )[src.full_id] = initial_data

        self.entity_graph.add_edge(src.full_id, dest.full_id)

    def connect_async_requests(self, src: AsyncModelFactory, dest: AsyncModelFactory):
        warnings.warn(
            "Connections using async_requests and the "
            "set_data function are deprecated and will be "
            "removed in a future release. Please use "
            "time_shifted and weak connections instead.",
            category=DeprecationWarning,
        )
        src_sim = self.sims[src._sid]
        dest_sim = self.sims[dest._sid]
        delay = connect_interval(src._group, dest._group)
        src_sim.successors[dest_sim] = delay
        src_sim.successors_to_wait_for[dest_sim] = delay
        dest_sim.input_delays.setdefault(src_sim, MinimalDurations()).insert(delay)

    def connect(
        self,
        src: Entity,
        dest: Entity,
        *attr_pairs: Union[str, Tuple[str, str]],  # type: ignore
        async_requests: bool = False,
        time_shifted: Union[bool, int] = False,
        initial_data: Dict[Attr, Any] = {},
        weak: bool = False,
        transform: Callable[[Any], Any] = lambda x: x,
    ):
        """
        Connect the *src* entity to *dest* entity.

        Establish a data-flow for each ``(src_attr, dest_attr)`` tuple
        in *attr_pairs*. If *src_attr* and *dest_attr* have the same
        name, you you can optionally only pass one of them as a single
        string.

        Raise a :exc:`~mosaik.exceptions.ScenarioError` if both entities
        share the same simulator instance, if at least one (src. or
        dest.) attribute in *attr_pairs* does not exist, or if the
        connection would introduce a cycle in the data-flow (e.g.,
        A → B → C → A).

        If the *dest* simulator may make asynchronous requests to mosaik
        to query data from *src* (or set data to it), *async_requests*
        should be set to ``True`` so that the *src* simulator stays in
        sync with *dest*.

        An alternative to asynchronous requests are time-shifted
        connections. Their data flow is always resolved after normal
        connections so that cycles in the data-flow can be realized
        without introducing deadlocks. For such a connection
        *time_shifted* should be set to ``True`` and *initial_data*
        should contain a dict with input data for the first simulation
        step of the receiving simulator.

        An alternative to using async_requests to realize cyclic
        data-flow is given by the time_shifted kwarg. If set to ``True``
        it marks the connection as cycle-closing (e.g. C → A). It must
        always be used with initial_data specifying a dict with the data
        sent to the destination simulator at the first step (e.g.
        *{'src_attr': value}*).
        """

        # Expand single attributes "attr" to ("attr", "attr") tuples:
        attr_pairs: Set[Tuple[Attr, Attr]] = {
            (a, a) if isinstance(a, str) else a for a in attr_pairs
        }
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
                    transform=transform,
                )
            except ScenarioError as e:
                errors.append(e)

        if async_requests:
            self.connect_async_requests(
                src.model_mock._factory, dest.model_mock._factory
            )

        if errors:
            raise ScenarioError(
                "While connecting entities, the following errors occurred:\n - "
                + "\n - ".join(str(e) for e in errors)
            )

        trigger: Set[Tuple[EntityId, Attr]] = set()
        for src_attr, dest_attr in attr_pairs:
            if dest.triggered_by(dest_attr):
                trigger.add((src.eid, src_attr))

        # Add relation in entity_graph
        self.entity_graph.add_edge(src.full_id, dest.full_id)

    def set_initial_event(self, sid: SimId, time: int = 0):
        """
        Set an initial step for simulator *sid* at time *time*
        (default=0).
        """
        sim = self.sims[sid]
        sim.next_steps = [TieredTime(time) + sim.from_world_time]

    async def get_data(
        self,
        entity_set: Iterable[Entity],
        *attributes: Attr,
    ) -> Dict[Entity, Dict[Attr, Any]]:
        """
        Get and return the values of all *attributes* for each entity of
        an *entity_set*.

        The return value is a dict mapping the entities of *entity_set*
        to dicts containing the values of each attribute in
        *attributes*::

            {
                Entity(...): {
                    'attr_1': 'val_1',
                    'attr_2': 'val_2',
                    ...
                },
                ...
            }
        """
        outputs_by_sim: Dict[SimId, OutputRequest] = defaultdict(dict)
        for entity in entity_set:
            outputs_by_sim[entity.sid][entity.eid] = list(attributes)

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

        results: Dict[Entity, Dict[Attr, Any]] = {}
        for entity in entity_set:
            results[entity] = results_by_sim[entity.sid][entity.eid]

        return results

    async def run(
        self,
        until: int,
        rt_factor: Optional[float] = None,
        rt_strict: bool = False,
        print_progress: Union[bool, Literal["individual"]] = False,
        lazy_stepping: bool = True,
    ):
        """Start the simulation and run it until the simulation time
        ``until`` is reached.

        As mosaik has no way of resetting simulators to their initial
        state, this method can only be called once.

        Unlike its counterpart :meth:`~mosaik.scenario.World.run` in the
        synchronous :class:`~mosaik.scenario.World`, this method will
        not automatically close the connection to connected simulators,
        even outside of a ``with`` block. You need to call
        :meth:`shutdown` manually afterwards (or use a ``with`` block).

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

        logger.info("Starting simulation.")
        # 11 is the length of "Total: 100%"
        max_sim_id_len = max(max(len(str(sid)) for sid in self.sims), 11)
        until_len = len(str(until))
        self.tqdm = tqdm(
            total=until,
            disable=not print_progress,
            colour="green",
            bar_format=(
                None
                if print_progress != "individual"
                else (
                    "Total:%s {percentage:3.0f}%% |{bar}| %s{elapsed}<{remaining}"
                    % (" " * (max_sim_id_len - 11), "  " * until_len)
                )
            ),
            unit="steps",
        )
        for sid, sim in self.sims.items():
            sim.tqdm = tqdm(
                total=until,
                desc=sid,
                bar_format=(
                    "{desc:>%i} |{bar}| {n_fmt:>%i}/{total_fmt}{postfix:10}"
                    % (max_sim_id_len, until_len)
                ),
                leave=False,
                disable=print_progress != "individual",
            )
        import mosaik._debug as dbg  # always import, enable when requested

        if self._debug:
            dbg.enable()
        success = False
        try:
            await scheduler.run(self, until, rt_factor, rt_strict, lazy_stepping)
            success = True
        except KeyboardInterrupt:
            logger.info("Simulation canceled. Terminating ...")
        except RemoteException as exc:
            logger.error(
                f"Simulator {exc.source} aborted the simulation with error "
                f"{exc.remote_type}({exc.remote_msg})."
                + (
                    " Further information provided:\n" + "\n".join(exc.further_args)
                    if exc.further_args
                    else ""
                )
            )
        finally:
            for sid, sim in self.sims.items():
                sim.tqdm.close()
            self.tqdm.close()
            if self._debug:
                dbg.disable()
            if success:
                logger.info("Simulation finished successfully.")

    def cache_triggering_ancestors(self):
        """Collects the ancestors of each simulator and stores them in
        the respective simulator object.
        """
        # See ``ensure_no_dataflow_cycles`` for an explanation of this
        # algorithm
        dirty: Set[SimRunner] = set()
        for sim in self.sims.values():
            for port_triggers in sim.triggers.values():
                for dest_sim, delay in port_triggers:
                    dest_sim.triggering_ancestors.setdefault(
                        sim, MinimalDurations()
                    ).insert(delay)
                    dirty.add(dest_sim)
        while dirty:
            sim = dirty.pop()
            for port_triggers in sim.triggers.values():
                for dest_sim, mid_to_dest in port_triggers:
                    for src_sim, src_to_mid in sim.triggering_ancestors.items():
                        src_to_dest = src_to_mid + mid_to_dest
                        was_updated = dest_sim.triggering_ancestors.setdefault(
                            src_sim, MinimalDurations()
                        ).insert_all(src_to_dest)
                        if was_updated:
                            dirty.add(dest_sim)
        return

    def ensure_no_dataflow_cycles(self):
        """Make sure that there is no cyclic dataflow with 0 total
        delay. Raise an exception with one such cycle otherwise.
        """

        # Short note on terminology: ancestors and descendants any
        # number of steps removed; predecessors and successors are one
        # step removed (i.e. they're *direct* ancestors/descendants)

        dirty: Set[SimRunner] = set(self.sims.values())
        """Sims that have changed descendants and thus require
        recalculation
        """
        sim_descs: Dict[SimRunner, Dict[SimRunner, MinPath]] = {
            sim: {} for sim in self.sims.values()
        }
        """For each SimRunner, all its descendants that have been found
        so far with the shortest delay to them and the path that
        exhibits this delay.
        """

        # At the start, enter each sim as a descendant of all its
        # (direct) predecessors
        for sim in self.sims.values():
            for pred, delay in sim.input_delays.items():
                min_durations = MinimalDurations()
                min_durations.insert_all(delay)
                sim_descs[pred][sim] = {
                    "delays": min_durations,
                    "path": [pred, sim],
                }
        while dirty:
            mid_sim = dirty.pop()
            # This sim has had updates to its descendants since we last
            # processed it. These changes are pushed to its predecessors
            for src_sim, src_to_mid_delays in mid_sim.input_delays.items():
                for dest_sim, mid_to_dest in sim_descs[mid_sim].items():
                    mid_to_dest_delays = mid_to_dest["delays"]
                    src_to_dest_delays = src_to_mid_delays + mid_to_dest_delays
                    was_updated = (
                        sim_descs[src_sim]
                        .setdefault(
                            dest_sim,
                            MinPath(
                                delays=MinimalDurations(),
                                path=[src_sim, dest_sim],
                            ),
                        )["delays"]
                        .insert_all(src_to_dest_delays)
                    )
                    if was_updated:
                        # In this case we need to update the
                        # predecessor's shortest path to the descendant
                        # and reprocess the predecessor
                        sim_descs[src_sim][dest_sim]["path"] = [
                            src_sim,
                            *mid_to_dest["path"],
                        ]
                        dirty.add(src_sim)

        # We need to raise an error if any sim has itself as a
        # descendant with a delay of 0
        for sim, descs in sim_descs.items():
            if sim not in descs:
                continue
            min_path = descs[sim]
            if min_path["delays"].contains_zero():
                raise ScenarioError(
                    f"Your scenario contains cycles, for example: {min_path['path']}."
                )

    async def shutdown(self):
        """
        Shut-down all simulators and close the server socket.
        """
        for sim in self.sims.values():
            await sim.stop()


class MinPath(TypedDict):
    delays: MinimalDurations
    path: List[SimRunner]


if TYPE_CHECKING:
    T = TypeVar("T", bound=SupportsRichComparison)


def update_min(a: T | None, b: T) -> T | None:
    if a is None:
        return b
    if a <= b:  # type: ignore
        return None
    return b


MOSAIK_METHODS = {
    "init",
    "create",
    "setup_done",
    "step",
    "get_data",
    "finalize",
    "stop",
}


FULL_ID = "%s.%s"


class ExtraMethodsProxy:
    _sim_id: SimId
    _methods: Set[str]

    def __init__(self, sim_id: SimId):
        self._sim_id = sim_id
        self._methods = set()

    def _add_extra_method(self, name: str, wrapper: Callable[..., Any]) -> None:
        setattr(self, name, wrapper)
        self._methods.add(name)

    def __iter__(self):
        return iter(self._methods)

    def __getattr__(self, name: str) -> Callable[..., Any]:
        raise ScenarioError(f"`{name}` is not an extra method on '{self._sim_id}'")


class AsyncModelFactory:
    """
    This is a facade for a simulator *sim* that allows the user to
    create new model instances (entities) within that simulator.

    For every model that a simulator publicly exposes, the
    :class:`AsyncModelFactory` provides a :class:`AsyncModelMock`
    attribute that actually creates the entities.

    If you access an attribute that is not a model or if the model is
    not marked as *public*, an :exc:`~mosaik.exceptions.ScenarioError`
    is raised.
    """

    type: Literal["event-based", "time-based", "hybrid"]
    models: Dict[ModelName, AsyncModelMock]
    entities: Dict[str, Entity]

    def __init__(  # noqa: C901
        self, world: AsyncWorld, group: SimGroup, sid: SimId, proxy: Proxy
    ):
        self.meta = proxy.meta
        self._world = world
        self._group = group
        self._proxy = proxy
        self._sid = sid
        self.call = ExtraMethodsProxy(sid)
        self.entities = {}

        if "type" not in proxy.meta:
            raise ScenarioError(
                'The simulator is missing a type specification ("time-based", '
                '"event-based" or "hybrid"). This is required starting from API '
                "version 3."
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
            self.models[model] = AsyncModelMock(self._world, self, model, self._proxy)
            # Make public models accessible
            if props.get("public", True):
                setattr(self, model, self.models[model])

        # Bind extra_methods to this instance:
        for meth_name in self.meta.get("extra_methods", []):
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

            # We need get_wrapper() in order to avoid problems with
            # scoping of the name `meth_name`. Without it, `meth_name`
            # would be the same for all wrappers.
            def get_wrapper(connection: Proxy, meth_name: str) -> Callable[..., Any]:
                async def wrapper(*args: Any, **kwargs: Any):
                    return await connection.send([meth_name, args, kwargs])

                wrapper.__name__ = meth_name
                return wrapper

            self.call._add_extra_method(meth_name, get_wrapper(proxy, meth_name))

    def __getattr__(self, name: str) -> AsyncModelMock:
        # Implemented in order to improve error messages.
        models = self.meta["models"]
        if name in models:
            raise AttributeError(f'Model "{name}" is not public.')
        else:
            raise AttributeError(
                f'Model factory for "{self._sid}" has no model and no function '
                f'"{name}".'
            )

    def validate_output_dict(self, eid_dict: OutputData):
        """
        Validate the structure and contents of an output dictionary.

        This method checks that the entities and attributes in the
        output dictionary are valid based on the simulator's internal
        state. If any entity in the output dictionary was not created
        during initialization, or if any attribute is not part of the
        entity's model's output attributes, a warning is issued to
        notify of potential errors in the simulator's
        :meth:`~Simulator.get_data` method.

        :param eid_dict: A dictionary of output data, where keys are
            entity IDs and values are dictionaries of attributes and
            their corresponding data.
        :raises UserWarning: If an entity ID in the output dictionary
            does not correspond to a known entity, or if an attribute is
            not part of the entity's model's defined output attributes.
        """
        for eid in eid_dict:
            if eid not in self.entities.keys():
                warnings.warn(
                    f"Simulator {self._sid} returned data for the entity {eid} which "
                    "was never created. This is likely an error in its get_data "
                    "method.",
                    UserWarning,
                )
            else:
                model_attrs = self.entities[eid].model_mock.output_attrs
                for attr in eid_dict[eid]:
                    if attr not in model_attrs:
                        warnings.warn(
                            f"Simulator {self._sid} returned data for attribute"
                            f"{attr} which does not exist in model "
                            f"{self.entities[eid].model_mock.name}. "
                            "This is likely an error in its get_data method.",
                            UserWarning,
                        )

    def get_progress(self):
        progress = self._world.sims[self._sid].progress
        return ProgressProxy(progress)


def parse_attrs(
    model_desc: ModelDescription, type: Literal["time-based", "event-based", "hybrid"]
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

    if model_desc.get("any_inputs", False):
        inputs: Optional[InOrOutSet[Attr]] = OutSet()
    else:
        inputs = wrap_set(model_desc.get("attrs"))
    empty: FrozenSet[Attr] = frozenset()
    if type == "time-based":
        default_measurements = None
        default_events = empty
    elif type == "event-based":
        default_measurements = empty
        default_events = None
    elif type == "hybrid":
        default_measurements = None if "trigger" in model_desc else inputs
        default_events = None
    measurement_inputs = wrap_set(model_desc.get("non-trigger", default_measurements))
    event_inputs = wrap_set(model_desc.get("trigger", default_events))
    measurement_inputs, event_inputs = parse_set_triple(
        inputs, measurement_inputs, event_inputs, "attrs", "non-trigger", "trigger"
    )
    if type == "time-based" and event_inputs != frozenset():
        raise ValueError(
            error_template % ("time-based", "trigger", "input", "non-trigger")
        )
    if type == "event-based" and measurement_inputs != frozenset():
        raise ValueError(
            error_template % ("event-based", "non-trigger", "inpus", "trigger")
        )

    outputs = wrap_set(model_desc.get("attrs"))
    default_measurements = empty if type == "event-based" else None
    measurement_outputs = wrap_set(model_desc.get("persistent", default_measurements))
    default_events = None if type == "event-based" else empty
    event_outputs = wrap_set(model_desc.get("non-persistent", default_events))
    measurement_outputs, event_outputs = parse_set_triple(
        outputs,
        measurement_outputs,
        event_outputs,
        "attrs",
        "persistent",
        "non-persistent",
    )
    if type == "time-based" and event_outputs != frozenset():
        raise ValueError(
            error_template % ("time-based", "non-persistent", "output", "persistent")
        )
    if type == "event-based" and measurement_outputs != frozenset():
        raise ValueError(
            error_template % ("event-based", "persistent", "output", "non-persistent")
        )

    return measurement_inputs, event_inputs, measurement_outputs, event_outputs


class AsyncModelMock(object):
    """
    Instances of this class are exposed as attributes of
    :class:`ModelFactory` and allow the instantiation of simulator
    models.

    You can *call* an instance of this class to create exactly one
    entity: ``sim.ModelName(x=23)``. Alternatively, you can use the
    :meth:`create` method to create multiple entities with the same set
    of parameters at once: ``sim.ModelName.create(3, x=23)``.
    """

    name: ModelName
    _world: AsyncWorld
    _factory: AsyncModelFactory
    _proxy: Proxy
    params: FrozenSet[str]
    event_inputs: InOrOutSet[Attr]
    measurement_inputs: InOrOutSet[Attr]
    event_outputs: InOrOutSet[Attr]
    measurement_outputs: InOrOutSet[Attr]

    def __init__(
        self,
        world: AsyncWorld,
        factory: AsyncModelFactory,
        model: ModelName,
        proxy: Proxy,
    ):
        self._world = world
        self._factory = factory
        self.name = model
        self._proxy = proxy
        model_desc = proxy.meta["models"][model]
        self.params = frozenset(model_desc.get("params", []))

        try:
            (
                self.measurement_inputs,
                self.event_inputs,
                self.measurement_outputs,
                self.event_outputs,
            ) = parse_attrs(model_desc, self._factory.type)
        except ValueError as e:
            raise ValueError(
                f"while parsing the model description of model {model} of the "
                f"simulator {factory._sid}: {e}"
            )

    @property
    def input_attrs(self) -> InOrOutSet[Attr]:
        return self.event_inputs | self.measurement_inputs

    @property
    def output_attrs(self) -> InOrOutSet[Attr]:
        return self.event_outputs | self.measurement_outputs

    async def __call__(self, **model_params: Any):
        """
        Call :meth:`create()` to instantiate one model.
        """
        return (await self.create(1, **model_params))[0]

    async def create(self, num: int, **model_params: Any):
        """
        Create *num* entities with the specified *model_params* and
        return a list with the entity dicts.

        The returned list of entities is the same as returned by
        :meth:`mosaik_api_v3.Simulator.create()`, but the simulator is
        prepended to every entity ID to make them globally unique.
        """
        self._check_params(**model_params)

        entities = await self._proxy.send(["create", (num, self.name), model_params])
        assert len(entities) == num, (
            f"{num} entities were requested but {len(entities)} were created."
        )

        return self._make_entities(entities, assert_type=self.name)

    def _check_params(self, **model_params: Any):
        unexpected_params = set(model_params.keys()).difference(self.params)
        if unexpected_params:
            sep = "', '"
            raise TypeError(
                "create() got unexpected keyword arguments: '"
                f"{sep.join(unexpected_params)}'"
            )

    def _make_entities(
        self,
        create_results: List[CreateResult],
        assert_type: Optional[ModelName] = None,
    ) -> List[Entity]:
        """
        Recursively create lists of :class:`Entity` instance from a list
        of *entity_dicts*.
        """
        sid = self._factory._sid
        entity_graph = self._world.entity_graph

        entity_set: List[Entity] = []
        for e in create_results:
            self._assert_model_type(assert_type, e)

            children = e.get("children")
            if children is not None:
                children = self._make_entities(children)
            model = self._factory.models[e["type"]]
            entity = Entity(
                sid, e["eid"], self.name, model, children, e.get("extra_info")
            )

            entity_set.append(entity)
            if entity.eid in self._factory.entities:
                raise DuplicateEntityIdError(sid, entity.eid)
            self._factory.entities[entity.eid] = entity
            entity_graph.add_node(entity.full_id, sid=sid, type=e["type"])
            for rel in e.get("rel", []):
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
            assert e["type"] == assert_type, (
                f'Entity "{e["eid"]}" has the wrong type: "{e["type"]}"; '
                f'"{assert_type}" required.'
            )
        else:
            assert e["type"] in self._proxy.meta["models"], (
                f'Type "{e["type"]}" of entity "{e["eid"]}" not found in sim\'s meta '
                "data."
            )


class Entity(object):
    """
    An entity represents an instance of a simulation model within
    mosaik.
    """

    __slots__ = ["sid", "eid", "sim_name", "model_mock", "children", "extra_info"]
    sid: SimId
    """The ID of the simulator this entity belongs to."""
    eid: EntityId
    """The entity's ID."""
    sim_name: str
    """The entity's simulator name."""
    model_mock: AsyncModelMock
    """The entity's type (or class)."""
    children: List[Entity]
    """An entity set containing subordinate entities."""
    extra_info: Any

    def __init__(
        self,
        sid: SimId,
        eid: EntityId,
        sim_name: str,
        model_mock: AsyncModelMock,
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
            f"{self.__class__.__name__}({self.full_id!r}, "
            f"model={self.model_mock.name!r})"
        )

    def __repr__(self):
        return (
            f"{self.__class__.__name__}(full_id={self.full_id!r}, "
            f"model_mock={self.model_mock!r}, children={self.children!r})"
        )
