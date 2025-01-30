"""
The simulation manager is responsible for starting simulation processes
and shutting them down. It also manages the communication between mosaik
and the processes.

It is able to start pure Python simulators in-process (by importing and
instantiating them), to start external simulation processes and to
connect to already running simulators and manage access to them.
"""

from __future__ import annotations

import asyncio
import collections
import heapq as hq
import importlib
import itertools
import os
import platform
import shlex
import subprocess
import sys
import warnings
from ast import literal_eval
from dataclasses import dataclass
from json import JSONEncoder
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Coroutine,
    Dict,
    List,
    NoReturn,
    Optional,
    OrderedDict,
    Tuple,
    Union,
    cast,
)

import mosaik_api_v3
import tqdm
from mosaik_api_v3.connection import Channel
from mosaik_api_v3.types import (
    Attr,
    EntityId,
    FullId,
    InputData,
    OutputData,
    OutputRequest,
    SimId,
    Time,
)
from typing_extensions import Literal, TypeAlias, TypedDict

from mosaik.adapters import init_and_get_adapter
from mosaik.exceptions import (
    NonSerializableOutputsError,
    ScenarioError,
    SimulationError,
)
from mosaik.progress import Progress
from mosaik.proxies import BaseProxy, LocalProxy, Proxy, RemoteProxy
from mosaik.tiered_time import MinimalDurations, TieredDuration, TieredTime

if "Windows" in platform.system():
    from subprocess import CREATE_NEW_CONSOLE  # type: ignore (only Windows)

if TYPE_CHECKING:
    from mosaik.async_scenario import (
        AsyncWorld,
        CmdModel,
        ConnectModel,
        PythonModel,
    )

FULL_ID_SEP = "."  # Separator for full entity IDs
FULL_ID = "%s.%s"  # Template for full entity IDs ('sid.eid')


class MosaikConfigTotal(TypedDict):
    """A total version for :class:`MosaikConfig` for internal use."""

    addr: Tuple[str, int | None]
    start_timeout: float
    stop_timeout: float


async def start(
    world: AsyncWorld,
    sim_name: str,
    sim_id: SimId,
    time_resolution: float,
    sim_params: Dict[str, Any],
) -> Proxy:
    """
    Start the simulator ``sim_name`` based on the configuration in
    :attr:`world.sim_config
    <mosaik.async_scenario.AsyncWorld.sim_config>`,
    give it the ID ``sim_id`` and pass the ``time_resolution`` and the
    parameter dict ``sim_params`` to it.

    :param world: the :class:`~mosaik.async_scenario.AsyncWorld` for the
        simulation
    :param sim_name: the name of the simulator in
        :attr:`world.sim_config
        <mosaik.async_scenario.AsyncWorld.sim_config>`
    :param sim_id: the ID of this simulator instance
    :param time_resolution: the number of seconds corresponding to one
        mosaik time steps
    :param sim_params: the additional keyword arguments given by the
        user when starting this simulator

    :return: the :class:`~mosaik.proxies.Proxy` representing the
        connection to this simulator
    """
    try:
        sim_config = world.sim_config[sim_name]
    except KeyError:
        raise ScenarioError(
            'Simulator "%s" could not be started: Not found in sim_config' % sim_name
        )

    # Try available starters in that order and raise an error if none of
    # them matches. Default starters are:
    # - python: start_inproc
    # - cmd: start_proc
    # - connect: start_connect
    starters = StarterCollection()

    for sim_type, starter in starters.items():
        if sim_type in sim_config:
            proxy = await starter(
                world.config, sim_name, sim_config, MosaikRemote(world, sim_id)
            )
            try:
                proxy = await asyncio.wait_for(
                    init_and_get_adapter(
                        proxy,
                        sim_id,
                        {"time_resolution": time_resolution, **sim_params},
                        explicit_version_str=sim_config.get("api_version"),
                    ),
                    world.config["start_timeout"],
                )
                return proxy
            except asyncio.IncompleteReadError:
                await proxy.stop()
                raise SystemExit(
                    f'Simulator "{sim_name}" closed its connection during the init() '
                    "call."
                )
            except asyncio.TimeoutError:
                await proxy.stop()
                raise SystemExit(
                    f'Simulator "{sim_name}" did not reply to the init() call in time.'
                )
    else:
        raise ScenarioError(
            f'Simulator "{sim_name}" could not be started: Invalid configuration'
        )


async def start_inproc(
    mosaik_config: MosaikConfigTotal,
    sim_name: str,
    sim_config: PythonModel,
    mosaik_remote: MosaikRemote,
) -> BaseProxy:
    """
    Import and instantiate the Python simulator ``sim_name`` based on
    its config entry ``sim_config``.

    :param mosaik_config: the configuration of mosaik itself
    :param sim_name: the name of the simulator to be started
    :param sim_config: the configuration of this specific simulator
    :param mosaik_remote: the object used by this simulator to make
        callbacks to mosaik

    :return: the :class:`~mosaik.proxise.LocalProxy` for this simulator

    :raise ~mosaik.exceptions.ScenarioError: if the simulator cannot be
        instantiated.
    """
    try:
        mod_name, cls_name = sim_config["python"].split(":")
        mod = importlib.import_module(mod_name)
        cls = getattr(mod, cls_name)
    except (AttributeError, ImportError, KeyError, ValueError) as err:
        detail_msgs = {
            ValueError: 'Malformed Python class name: Expected "module:Class"',
            ModuleNotFoundError: "Could not import module: %s" % err.args[0],
            AttributeError: "Class not found in module",
            ImportError: f"Error importing the requested class: {err.args[0]}",
            KeyError: "'python' key not found in sim_config. "
            "(This is an error in mosaik, please report it.)",
        }
        details = detail_msgs[type(err)]
        origerr = err.args[0]
        raise ScenarioError(
            'Simulator "%s" could not be started: %s --> %s'
            % (sim_name, details, origerr)
        ) from None
    sim = cls()

    if int(mosaik_api_v3.__version__.split(".")[0]) < 3:
        raise ScenarioError("Mosaik 3 requires mosaik_api_v3 or newer.")

    return LocalProxy(sim, mosaik_remote)


async def start_proc(
    mosaik_config: MosaikConfigTotal,
    sim_name: str,
    sim_config: CmdModel,
    mosaik_remote: MosaikRemote,
) -> BaseProxy:
    """
    Start a new process for simulator *sim_name* based on its config
    entry *sim_config*.

    Return a :class:`RemoteProcess` instance.

    Raise a :exc:`~mosaik.exceptions.ScenarioError` if the simulator
    cannot be instantiated.
    """
    channel_future: asyncio.Future[Channel] = asyncio.Future()

    async def on_connect(r: asyncio.StreamReader, w: asyncio.StreamWriter):
        channel_future.set_result(Channel(r, w, name=sim_name))

    server = await asyncio.start_server(on_connect, *mosaik_config["addr"])
    try:
        actual_addr = server.sockets[0].getsockname()

        replacements = {
            "addr": "%s:%s" % actual_addr,
            "python": sys.executable,
        }
        cmd = sim_config["cmd"] % replacements
        posix = sim_config.pop("posix", os.name != "nt")
        cmd = shlex.split(cmd, posix=bool(posix))
        cwd = sim_config.get("cwd", ".")

        # Make a copy of the current env vars dictionary and update it
        # with the user provided values (or an empty dict as a default):
        env = dict(os.environ)
        env.update(sim_config.get("env", {}))

        # CREATE_NEW_CONSOLE constant for subprocess is only available
        # on Windows
        creationflags: int = 0
        new_console = sim_config.get("new_console", False)
        if new_console:
            if "Windows" in platform.system():
                creationflags = cast(int, CREATE_NEW_CONSOLE)  # type: ignore
            else:
                warnings.warn(
                    f'Simulator "{sim_name}" could not be started in a new console: '
                    "Only available on Windows"
                )

        try:
            proc = subprocess.Popen(
                cmd,
                bufsize=1,
                cwd=cwd,
                universal_newlines=True,
                env=env,  # pass the new env dict to the sub process
                creationflags=creationflags,
            )
        except (FileNotFoundError, NotADirectoryError) as e:
            # This distinction has to be made due to a change in python
            # 3.8.0. It might become unecessary for future releases
            # supporting python >= 3.8 only.
            if str(e).count(":") == 2:
                eout = e.args[1]
            else:
                eout = str(e).split("] ")[1]
            raise ScenarioError(
                f'Simulator "{sim_name}" could not be started: {eout}'
            ) from None

        try:
            channel = await asyncio.wait_for(
                channel_future, timeout=mosaik_config["start_timeout"]
            )
            return RemoteProxy(
                channel,
                mosaik_remote,
                process=(proc, sim_config.get("auto_terminate", True)),
            )
        except asyncio.TimeoutError:
            if sim_config.get("auto_terminate", True):
                proc.terminate()
            raise SimulationError(
                f'Simulator "{sim_name}" did not connect to mosaik in time.'
            )
    finally:
        server.close()


async def start_connect(
    mosaik_config: MosaikConfigTotal,
    sim_name: str,
    sim_config: ConnectModel,
    mosaik_remote: MosaikRemote,
) -> BaseProxy:
    """
    Connect to the already running simulator *sim_name* based on its
    config entry *sim_config*.

    Return a :class:`RemoteProcess` instance.

    Raise a :exc:`~mosaik.exceptions.ScenarioError` if the simulator
    cannot be instantiated.
    """
    addr = sim_config["connect"]
    try:
        host, port = addr.strip().split(":")
        addr = (host, int(port))
    except ValueError:
        raise ScenarioError(
            f'Simulator "{sim_name}" could not be started: Could not parse address '
            f'"{sim_config["connect"]}"'
        ) from None

    try:
        reader, writer = await asyncio.open_connection(host, port)
    except (ConnectionError, OSError):
        raise SimulationError(
            f'Simulator "{sim_name}" could not be started: Could not connect to '
            f'"{sim_config["connect"]}"'
        )
    return RemoteProxy(Channel(reader, writer, name=sim_name), mosaik_remote)


Port: TypeAlias = Tuple[EntityId, Attr]
"""Pair of an entity ID and an attribute of that entity"""


@dataclass
class PushDescription:
    """
    Describes a connection for pushing data from one simulator to
    another.

    :param dest_sim: The :class:`SimRunner` instance representing the
        simulator receiving the data.
    :param delay: The `TieredDuration` representing the time shift (or
        delay) applied to the data during transmission along the
        connection.
    :param dest_port: The `Port` representing the entity-attribute pair
        for the destination in the target simulator.
    :param transform: A callable function applied to the data as it
        is pushed to the destination.
    """

    dest_sim: SimRunner
    delay: TieredDuration
    dest_port: Port
    transform: Callable[..., Any]


@dataclass
class PullDescription:
    """
    Describes a connection for pulling data into a simulator.

    :param src_port: The `Port` representing the entity-attribute pair
        from which data is pulled in the connected simulator.
    :param dest_port: The `Port` representing the entity-attribute pair
        that is the destination for the pulled data.
    :param transform: A callable function applied to the data as it is
        forwarded to its destination.
    """

    src_port: Port
    dest_port: Port
    transform: Callable[..., Any]


class SimRunner:
    """
    Handler for an external simulator.

    It stores its simulation state and own the proxy object to the
    external simulator.
    """

    sid: SimId
    """This simulator's ID."""
    type: Literal["time-based", "event-based", "hybrid"]
    supports_set_events: bool

    _proxy: Proxy
    """The actual proxy for this simulator."""

    # Connection setup
    input_delays: Dict[SimRunner, MinimalDurations]
    """For each simulator that provides data to this simulator, the
    minimum over all input delays. This is used while waiting for
    dependencies.
    """
    # TODO: Saving the minimal durations here might actually be wrong.
    # We probably want to save *all* triggering durations.
    triggers: Dict[Port, List[Tuple[SimRunner, TieredDuration]]]
    """For each port of this simulator, the simulators that are
    triggered by output on that port and the delay accrued along that
    edge.
    """
    successors: Dict[SimRunner, TieredDuration]
    """The immediate successors of this simulator. This is used when
    lazy stepping to ensure that we don't step ahead too far. Therefore,
    the duration is only used as an adapter, and will always have all
    tiers 0. (Thus, we don't need `MinimalDurations` here.)
    """
    successors_to_wait_for: Dict[SimRunner, TieredDuration]
    """The immediate successors that we always need to wait for (due
    to async requests.) The duration only serves as an adapter (so we
    don't need `MinimalDurations` here.)
    """
    triggering_ancestors: Dict[SimRunner, MinimalDurations]
    """An iterable of this sim's ancestors that can trigger a step of
    this simulator. The second component specifies the least amount of
    time that output from the ancestor needs to reach us.
    """
    pulled_inputs: Dict[Tuple[SimRunner, TieredDuration], List[PullDescription]]
    """Output to pull in whenever this simulator performs a step.
    The keys are the source :class:`SimRunner` and the time shift, the
    values are lists of :class:`PullDescription` objects. Each
    :class:`PullDescription` specifies the source and destination
    entity-attribute pairs along with an optional transformation
    function applied to the data.
    """
    output_to_push: Dict[Port, List[PushDescription]]
    """This lists those connections that use the timed_input_buffer.
    The keys are the entity-attribute pairs (Port) of this simulator,
    and the values are lists of :class:`PushDescription` objects. Each
    PushDescription specifies the destination simulator, the
    entity-attribute pair for the target, and the time shift occurring
    along the connection.
    """

    to_world_time: TieredDuration
    from_world_time: TieredDuration

    output_request: OutputRequest

    inputs_from_set_data: InputData
    """Inputs received via `set_data`."""
    persistent_inputs: InputData
    """Memory of previous inputs for persistent attributes."""
    timed_input_buffer: TimedInputBuffer
    """Inputs for this simulator."""

    rt_start: float  # type: ignore  # set at start of sim_process
    """The real time when this simulator started (as returned by
    `perf_counter()`."""
    started: bool

    next_steps: List[TieredTime]
    """The scheduled next steps this simulator will take, organized as a
    heap. Once the immediate next step has been chosen (and the
    :attr:`has_next_step` event has been triggered), the step is moved
    to :attr:`next_step` instead.
    """
    newer_step: asyncio.Event
    next_self_step: Optional[TieredTime]
    """The next self-scheduled step for this simulator."""

    progress: Progress
    """This simulator's progress in mosaik time.

    This simulator has done all its work before time :attr:`progress`,
    so other simulator can rely on this simulator's output until this
    time.
    """
    last_step: TieredTime
    """The most recent step this simulator performed."""
    current_step: Optional[TieredTime]

    output_time: TieredTime  # type: ignore  # set on first get_data
    """The output time associated with `data`. Usually, this will be
    equal to `last_step` but simulators may specify a different time for
    their output.
    """
    data: OutputData  # type: ignore  # set on first get_data
    """The newest data returned by this simulator."""
    task: asyncio.Task[None]
    """The asyncio.Task for this simulator."""

    outputs: Optional[Dict[Time, OutputData]]
    tqdm: tqdm.tqdm[NoReturn]  # type: ignore
    check_outputs: Callable[[OutputData], None]

    def __init__(
        self,
        sid: SimId,
        connection: Proxy,
        check_outputs: Callable[[OutputData], None],
        depth: int = 1,
    ):
        self.check_outputs = check_outputs
        self.sid = sid
        self._proxy = connection

        self.type = connection.meta["type"]
        self.supports_set_events = connection.meta.get("set_events", False)
        # Simulation state
        self.started = False
        self.last_step = TieredTime(-1, *([0] * (depth - 1)))
        self.current_step = None
        if self.type != "event-based":
            self.next_steps = [TieredTime(*([0] * depth))]
        else:
            self.next_steps = []
        self.next_self_step = None
        self.progress = Progress(TieredTime(*([0] * depth)))

        self.to_world_time = TieredDuration(0, cutoff=1, pre_length=depth)
        self.from_world_time = TieredDuration(*([0] * depth), cutoff=1, pre_length=1)

        self.inputs_from_set_data = {}
        self.persistent_inputs = {}
        self.timed_input_buffer = TimedInputBuffer()

        self.successors_to_wait_for = {}
        self.successors = {}
        self.triggering_ancestors = {}
        self.triggers = {}
        self.output_to_push = {}
        self.pulled_inputs = {}

        self.task = None  # type: ignore  # will be set in World.run
        self.newer_step = asyncio.Event()
        self.is_in_step = False

        self.input_delays = {}

        self.output_request = {}

        self.outputs = None

    def schedule_step(self, tiered_time: TieredTime):
        """Schedule a step for this simulator at the given time. This
        will trigger a re-evaluation whether this simulator's next
        step is settled, provided that the new step is earlier than the
        old one and the simulator is currently awaiting it's next
        settled step.
        """
        if tiered_time in self.next_steps:
            return tiered_time

        is_earlier = not self.next_steps or tiered_time < self.next_steps[0]
        hq.heappush(self.next_steps, tiered_time)
        if is_earlier:
            self.newer_step.set()

    async def setup_done(self):
        return await self._proxy.send(["setup_done", (), {}])

    async def step(
        self, time: Time, inputs: InputData, max_advance: Time
    ) -> Optional[Time]:
        try:
            return await self._proxy.send(["step", (time, inputs, max_advance), {}])
        except TypeError:  # from JSON serialization
            # Find source for more precise error message
            encoder = JSONEncoder()
            error = NonSerializableOutputsError(self.sid)
            for dest_eid, entity_inputs in inputs.items():
                for dest_attr, attr_inputs in entity_inputs.items():
                    for src_id, value in attr_inputs.items():
                        try:
                            encoder.encode(value)
                        except TypeError as e:
                            error.add_error(dest_eid, dest_attr, src_id, e)
            if error:
                raise error
            else:  # no culprits found, raise original exception
                raise

    async def get_data(self, outputs: OutputRequest) -> OutputData:
        return await self._proxy.send(["get_data", (outputs,), {}])

    def get_output_for(self, time: Time) -> OutputData:
        assert self.outputs is not None
        for data_time, value in reversed(self.outputs.items()):
            if data_time <= time:
                return value

        return {}

    async def stop(self):
        """
        Stop the simulator behind the proxy.
        """
        await self._proxy.stop()

    def __repr__(self):
        return f"<{self.__class__.__name__} sid={self.sid!r}>"


class MosaikRemote(mosaik_api_v3.MosaikProxy):
    world: AsyncWorld
    sid: SimId

    def __init__(self, world: AsyncWorld, sid: SimId):
        self.world = world
        self.sid = sid

    @property
    def sim(self):
        return self.world.sims[self.sid]

    async def get_progress(self) -> float:
        """
        Return the current simulation progress from
        :attr:`~mosaik.async_scenario.AsyncWorld.sim_progress`.
        """
        return self.world.sim_progress

    async def get_related_entities(
        self, entities: Union[FullId, List[FullId], None] = None
    ) -> Union[Dict[str, Any], Dict[str, Dict[str, Any]]]:
        """
        Return information about the related entities of *entities*.

        If *entities* omitted (or ``None``), return the complete entity
        graph, e.g.::

            {
                'nodes': {
                    'sid_0.eid_0': {'type': 'A'},
                    'sid_0.eid_1': {'type': 'B'},
                    'sid_1.eid_0': {'type': 'C'},
                },
                'edges': [
                    ['sid_0.eid_0', 'sid_1.eid0', {}],
                    ['sid_0.eid_1', 'sid_1.eid0', {}],
                ],
            }

        If *entities* is a single string (e.g., ``sid_1.eid_0``), return
        a dict containing all entities related to that entity::

            {
                'sid_0.eid_0': {'type': 'A'},
                'sid_0.eid_1': {'type': 'B'},
            }

        If *entities* is a list of entity IDs (e.g., ``['sid_0.eid_0',
        'sid_0.eid_1']``), return a dict mapping each entity to a dict
        of related entities::

            {
                'sid_0.eid_0': {
                    'sid_1.eid_0': {'type': 'B'},
                },
                'sid_0.eid_1': {
                    'sid_1.eid_1': {'type': 'B'},
                },
            }
        """
        graph = self.world.entity_graph
        if entities is None:
            # repackage NodeViews and EdgeViews to maintain
            # compatibility
            nodes_list = literal_eval(str(graph.nodes(data=True)))
            nodes_dict = {node[0]: node[1] for node in nodes_list}

            edges_list = literal_eval(str(graph.edges))
            edges_tuple = tuple(list(edge) + [{}] for edge in edges_list)

            return {"nodes": nodes_dict, "edges": edges_tuple}
        elif isinstance(entities, str):
            return {n: graph.nodes[n] for n in graph[entities]}
        else:
            return {eid: {n: graph.nodes[n] for n in graph[eid]} for eid in entities}

    async def get_data(self, attrs: Dict[FullId, List[Attr]]) -> Dict[str, Any]:
        """
        .. warning::
            This method is deprecated and will be removed in a future
            release. Implement cyclic data flow using time-shifted and
            weak connections instead.

        Return the data for the requested attributes *attrs*.

        *attrs* is a dict of (fully qualified) entity IDs mapping to
        lists of attribute names (``{'sid/eid': ['attr1', 'attr2']}``).

        The return value is a dictionary, which maps the input entity
        IDs to data dictionaries, which in turn map attribute names to
        their respective values: (``{'sid/eid': {'attr1': val1, 'attr2':
        val2}}``).
        """
        assert self.sim.is_in_step, "get_data must happen in step"
        assert self.sim.current_step is not None, "no current step time"

        data: Dict[FullId, Dict[Attr, Any]] = {}
        missing: Dict[SimId, OutputRequest] = collections.defaultdict(
            lambda: collections.defaultdict(list)
        )
        # Try to get data from cache
        for full_id, attr_names in attrs.items():
            sid, eid = full_id.split(FULL_ID_SEP, 1)
            src_sim = self.world.sims[sid]
            # Check if async_requests are enabled.
            self._assert_async_requests(src_sim, self.sim)
            if self.world.use_cache:
                cache_slice = src_sim.get_output_for(self.sim.last_step.time)
            else:
                cache_slice = {}

            data[full_id] = {}
            for attr in attr_names:
                try:
                    data[full_id][attr] = cache_slice[eid][attr]
                except KeyError:
                    missing[sid][eid].append(attr)

        # Query simulator for data not in the cache
        for sid, attrs in missing.items():
            dep = self.world.sims[sid]
            dep_data = await dep._proxy.send(["get_data", (attrs,), {}])
            for eid, vals in dep_data.items():
                # Maybe there's already an entry for full_id, so we need
                # to update the dict in that case.
                data.setdefault(FULL_ID % (sid, eid), {}).update(vals)

        return data

    async def set_data(self, data: Dict[FullId, Dict[Attr, Any]]):
        """
        .. warning::
            This method is deprecated and will be removed in a future
            release. Implement cyclic data flow using time-shifted and
            weak connections instead.

        Set *data* as input data for all affected simulators.

        *data* is a dictionary mapping source entity IDs to destination
        entity IDs with dictionaries of attributes and values
        (``{'src_full_id': {'dest_full_id': {'attr1': 'val1', 'attr2':
        'val2'}}}``).
        """
        for src_full_id, dest in data.items():
            for full_id, attributes in dest.items():
                sid, eid = full_id.split(FULL_ID_SEP, 1)
                src_sim = self.world.sims[sid]
                self._assert_async_requests(src_sim, self.sim)
                inputs = src_sim.inputs_from_set_data.setdefault(eid, {})
                for attr, val in attributes.items():
                    inputs.setdefault(attr, {})[src_full_id] = val

    async def set_event(self, event_time: Time):
        """
        Schedules an event/step at simulation time *event_time*.
        """
        sim = self.world.sims[self.sid]
        if not self.world.rt_factor:
            raise SimulationError(
                f"Simulator '{self.sid}' tried to set an event in non-real-time mode."
            )
        if event_time < self.world.until:
            sim.schedule_step(TieredTime(event_time))
        else:
            warnings.warn(
                f"Event set at {event_time} by {sim.sid} is after simulation end "
                f"{self.world.until} and will be ignored.",
                UserWarning,
            )

    def _assert_async_requests(self, src_sim: SimRunner, dest_sim: SimRunner):
        """
        Check if async. requests are allowed from *dest_sid* to
        *src_sid* and raise a :exc:`ScenarioError` if not.
        """
        if dest_sim not in src_sim.successors:
            raise ScenarioError(
                f"No connection from {src_sim.sid} to {dest_sim.sid}: You need to "
                "connect entities from both simulators and set `async_requests=True`."
            )
        if dest_sim not in src_sim.successors_to_wait_for:
            raise ScenarioError(
                f"Async. requests not enabled for the connection from {src_sim.sid} to "
                f"{dest_sim.sid}. Add the argument `async_requests=True` to the "
                f"connection of entities from {src_sim.sid} to {dest_sim.sid}."
            )


class StarterCollection(object):
    """
    This class provides a singleton instance of a collection of
    simulation starters. Default starters are:
    - python: start_inproc
    - cmd: start_proc
    - connect: start_connect

    External packages may add additional methods of starting simulations
    by adding new elements::

        from mosaik.simmanager import StarterCollection
        s = StarterCollection()
        s['my_starter'] = my_starter_func
    """

    # Singleton instance of the starter collection.
    __instance: (
        OrderedDict[str, Callable[..., Coroutine[Any, Any, BaseProxy]]] | None
    ) = None

    def __new__(cls) -> OrderedDict[str, Callable[..., Coroutine[Any, Any, BaseProxy]]]:
        if StarterCollection.__instance is None:
            # These are the starters defined by mosaik itself:
            StarterCollection.__instance = collections.OrderedDict(
                python=start_inproc, cmd=start_proc, connect=start_connect
            )

        return StarterCollection.__instance


class TimedInputBuffer:
    """
    A buffer to store inputs with its corresponding *time*.

    When the data is queried for a specific *step* time, all entries
    with *time* <= *step* are added to the input_dictionary.

    If there are several entries for the same connection at the same
    time, only the most recent value is added.
    """

    input_queue: List[Tuple[Time, int, FullId, EntityId, Attr, Any]]

    def __init__(self):
        self.input_queue = []
        self.counter = itertools.count()  # Used to chronologically sort entries

    def add(
        self,
        time: Time,
        src_sid: SimId,
        src_eid: EntityId,
        dest_eid: EntityId,
        dest_attr: Attr,
        value: Any,
    ):
        src_full_id = f"{src_sid}.{src_eid}"
        hq.heappush(
            self.input_queue,
            (time, next(self.counter), src_full_id, dest_eid, dest_attr, value),
        )

    def get_input(self, input_dict: InputData, step: Time) -> InputData:
        while len(self.input_queue) > 0 and self.input_queue[0][0] <= step:
            _, _, src_full_id, eid, attr, value = hq.heappop(self.input_queue)
            input_dict.setdefault(eid, {}).setdefault(attr, {})[src_full_id] = value

        return input_dict

    def __bool__(self):
        return bool(len(self.input_queue))
