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
import itertools
import warnings
from ast import literal_eval
from dataclasses import dataclass
from json import JSONEncoder
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    List,
    NoReturn,
    Optional,
    Tuple,
    Union,
)

import mosaik_api_v3
import tqdm
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
from typing_extensions import Literal, TypeAlias

from mosaik.exceptions import (
    NonSerializableOutputsError,
    ScenarioError,
    SimulationError,
)
from mosaik.progress import Progress
from mosaik.proxies import Proxy
from mosaik.tiered_time import MinimalDurations, TieredDuration, TieredTime

if TYPE_CHECKING:
    from mosaik.async_scenario import AsyncWorld, SimGroup

FULL_ID_SEP = "."  # Separator for full entity IDs
FULL_ID = "%s.%s"  # Template for full entity IDs ('sid.eid')


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
    transform: Callable[[Any], Any] = lambda x: x


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
    transform: Callable[[Any], Any] = lambda x: x


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

    group: SimGroup | None

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
        group: SimGroup | None = None,
    ):
        self.check_outputs = check_outputs
        self.sid = sid
        self._proxy = connection
        self.group = group

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
        return self.world._get_sim_runners()[self.sid]

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
            src_sim = self.world._get_sim_runners()[sid]
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
            dep = self.world._get_sim_runners()[sid]
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
                src_sim = self.world._get_sim_runners()[sid]
                self._assert_async_requests(src_sim, self.sim)
                inputs = src_sim.inputs_from_set_data.setdefault(eid, {})
                for attr, val in attributes.items():
                    inputs.setdefault(attr, {})[src_full_id] = val

    async def set_event(self, event_time: Time):
        """
        Schedules an event/step at simulation time *event_time*.
        """
        sim = self.world._get_sim_runners()[self.sid]
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
