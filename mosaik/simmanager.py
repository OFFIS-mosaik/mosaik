"""
The simulation manager is responsible for starting simulation processes and
shutting them down. It also manages the communication between mosaik and the
processes.

It is able to start pure Python simulators in-process (by importing and
instantiating them), to start external simulation processes and to connect to
already running simulators and manage access to them.
"""
from __future__ import annotations

from ast import literal_eval
import asyncio
import collections
from dataclasses import dataclass
import heapq as hq
import importlib
import itertools
import os
import shlex
import subprocess
import sys
from loguru import logger
from typing import (
    Any,
    Callable,
    Coroutine,
    Dict,
    Iterable,
    List,
    Optional,
    OrderedDict,
    Set,
    Tuple,
    TYPE_CHECKING,
    Union,
)
from typing_extensions import Literal

import mosaik_api
from mosaik_api.connection import Channel
from mosaik_api.types import CreateResult, Meta, ModelName, OutputData, OutputRequest, SimId, Time, InputData, Attr, EntityId
from mosaik.dense_time import DenseTime

from mosaik.exceptions import ScenarioError, SimulationError
from mosaik.progress import Progress
from mosaik.proxies import Proxy, LocalProxy, BaseProxy, RemoteProxy
from mosaik.adapters import init_and_get_adapter

if TYPE_CHECKING:
    import tqdm
    from mosaik.scenario import World, DataflowEdge

FULL_ID_SEP = '.'  # Separator for full entity IDs
FULL_ID = '%s.%s'  # Template for full entity IDs ('sid.eid')


async def start(
    world: World,
    sim_name: str,
    sim_id: SimId,
    time_resolution: float,
    sim_params: Dict[str, Any],
) -> Proxy:
    """
    Start the simulator *sim_name* based on the configuration im
    *world.sim_config*, give it the ID *sim_id* and pass the time_resolution
    and the parameters of the dict *sim_params* to it.

    The sim config is a dictionary with one entry for every simulator. The
    entry itself tells mosaik how to start the simulator::

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

    *ExampleSimA* is a pure Python simulator. Mosaik will import the module
    ``example_sim.mosaik`` and instantiate the class ``ExampleSim`` to start
    the simulator.

    *ExampleSimB* would be started by executing the command *example_sim* and
    passing the network address of mosaik das command line argument. You can
    optionally specify a *current working directory*. It defaults to ``.``.

    *ExampleSimC* can not be started by mosaik, so mosaik tries to connect to
    it.

    *time_resolution* (in seconds) is a global scenario parameter, which tells
    the simulators what the integer time step means in seconds. Its default
    value is 1., meaning one integer step corresponds to one second simulated
    time.

    The function returns a :class:`mosaik_api.Simulator` instance.

    It raises a :exc:`~mosaik.exceptions.SimulationError` if the simulator
    could not be started.

    Return a :class:`SimProxy` instance.
    """
    try:
        sim_config = world.sim_config[sim_name]
    except KeyError:
        raise ScenarioError('Simulator "%s" could not be started: Not found '
                            'in sim_config' % sim_name)

    # Try available starters in that order and raise an error if none of them
    # matches. Default starters are:
    # - python: start_inproc
    # - cmd: start_proc
    # - connect: start_connect
    starters = StarterCollection()

    for sim_type, starter in starters.items():
        if sim_type in sim_config:
            proxy = await starter(world, sim_name, sim_config, MosaikRemote(world, sim_id))
            try:
                proxy = await asyncio.wait_for(
                    init_and_get_adapter(proxy, sim_id, {"time_resolution": time_resolution, **sim_params}),
                    world.config['start_timeout']
                )
                return proxy
            except asyncio.IncompleteReadError:
                raise SystemExit(
                    f'Simulator "{sim_name}" closed its connection during the init() '
                    'call.'
                )
            except asyncio.TimeoutError:
                raise SystemExit(
                    f'Simulator "{sim_name}" did not reply to the init() call in time.'
                )
    else:
        raise ScenarioError(
            f'Simulator "{sim_name}" could not be started: Invalid configuration'
        )


async def start_inproc(
    world: World,
    sim_name: str,
    sim_config: Dict[Literal['python', 'env'], str],
    mosaik_remote: MosaikRemote,
) -> BaseProxy:
    """
    Import and instantiate the Python simulator *sim_name* based on its
    config entry *sim_config*.

    Return a :class:`LocalProcess` instance.

    Raise a :exc:`~mosaik.exceptions.ScenarioError` if the simulator cannot be
    instantiated.
    """
    try:
        mod_name, cls_name = sim_config['python'].split(':')
        mod = importlib.import_module(mod_name)
        cls = getattr(mod, cls_name)
    except (AttributeError, ImportError, KeyError, ValueError) as err:
        detail_msgs = {
            ValueError: 'Malformed Python class name: Expected "module:Class"',
            ModuleNotFoundError: 'Could not import module: %s' % err.args[0],
            AttributeError: 'Class not found in module',
            ImportError: f"Error importing the requested class: {err.args[0]}",
            KeyError:
                "'python' key not found in sim_config. "
                "(This is an error in mosaik, please report it.)",
        }
        details = detail_msgs[type(err)]
        origerr = err.args[0]
        raise ScenarioError('Simulator "%s" could not be started: %s --> %s' %
                            (sim_name, details, origerr)) from None
    sim = cls()

    if int(mosaik_api.__version__.split('.')[0]) < 3:
        raise ScenarioError("Mosaik 3 requires mosaik_api's version also "
                            "to be >=3.")

    return LocalProxy(sim, mosaik_remote)


async def start_proc(
    world: World,
    sim_name: str,
    sim_config: Dict[Literal['cmd', 'cwd', 'env', 'posix'], str],
    mosaik_remote: MosaikRemote,
) -> BaseProxy:
    """
    Start a new process for simulator *sim_name* based on its config entry
    *sim_config*.

    Return a :class:`RemoteProcess` instance.

    Raise a :exc:`~mosaik.exceptions.ScenarioError` if the simulator cannot be
    instantiated.
    """
    replacements = {
        'addr': '%s:%s' % (world.config['addr'][0], world.config['addr'][1]),
        'python': sys.executable,
    }
    cmd = sim_config['cmd'] % replacements
    if 'posix' in sim_config.keys():
        posix = sim_config.pop('posix')
        cmd = shlex.split(cmd, posix=bool(posix))
    else:
        cmd = shlex.split(cmd, posix=(os.name != 'nt'))
    cwd = sim_config['cwd'] if 'cwd' in sim_config else '.'

    # Make a copy of the current env. vars dictionary and update it with the
    # user provided values (or an empty dict as a default):
    env = dict(os.environ)
    env.update(sim_config.get('env', {}))  # type: ignore

    kwargs = {
        'bufsize': 1,
        'cwd': cwd,
        'universal_newlines': True,
        'env': env,  # pass the new env dict to the sub process
    }
    try:
        subprocess.Popen(cmd, **kwargs)
    except (FileNotFoundError, NotADirectoryError) as e:
        # This distinction has to be made due to a change in python 3.8.0.
        # It might become unecessary for future releases supporting
        # python >= 3.8 only.
        if str(e).count(':') == 2:
            eout = e.args[1]
        else:
            eout = str(e).split('] ')[1]
        raise ScenarioError('Simulator "%s" could not be started: %s'
                            % (sim_name, eout)) from None

    try:
        channel = await asyncio.wait_for(
            world.incoming_connections_queue.get(),
            world.config['start_timeout'],
        )
        return RemoteProxy(channel, mosaik_remote)
    except asyncio.TimeoutError:
        raise SimulationError(
            f'Simulator "{sim_name}" did not connect to mosaik in time.'
        )


async def start_connect(
    world: World,
    sim_name: str,
    sim_config,
    mosaik_remote: MosaikRemote,
) -> BaseProxy:
    """
    Connect to the already running simulator *sim_name* based on its config
    entry *sim_config*.

    Return a :class:`RemoteProcess` instance.

    Raise a :exc:`~mosaik.exceptions.ScenarioError` if the simulator cannot be
    instantiated.
    """
    addr = sim_config['connect']
    try:
        host, port = addr.strip().split(':')
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
    return RemoteProxy(Channel(reader, writer), mosaik_remote)


@dataclass
class PredecessorInfo:
    time_shift: int
    is_weak: bool
    triggering: bool

    wait_async: asyncio.Event

    pulled_inputs: Iterable[Tuple[EntityId, EntityId, Iterable[Tuple[Attr, Attr]]]]
    """Inputs that this simulator pulls from its predecessor using that
    SimRunner's get_output_for method.

    The structure is an iterable of (src_eid, dest_eid, attrs) triples
    where attrs is an iterable of the corresponding
    (src_attr, dets_attr) pairs.
    """


@dataclass
class SuccessorInfo:
    time_shift: int
    is_weak: bool
    delay: DenseTime
    pred_waiting: bool

    trigger: Set[Tuple[EntityId, Attr]]
    
    wait_async: asyncio.Event


class SimRunner:
    """
    Handler for an external simulator.

    It stores its simulation state and own the proxy object to the external
    simulator.
    """

    sid: SimId
    """This simulator's ID."""
    type: Literal['time-based', 'event-based', 'hybrid']
    supports_set_events: bool

    _proxy: Proxy
    """The actual proxy for this simulator."""

    rt_start: float
    """The real time when this simulator started (as returned by
    `perf_counter()`."""
    started: bool

    next_steps: List[DenseTime]
    """The scheduled next steps this simulator will take, organized as a heap.
    Once the immediate next step has been chosen (and the `has_next_step` event
    has been triggered), the step is moved to `next_step` instead."""
    newer_step: asyncio.Event
    next_self_step: Optional[Time]
    """The next self-scheduled step for this simulator."""

    predecessors: Dict[SimRunner, PredecessorInfo]
    """This simulator's predecessors in the dataflow graph and the
    corresponding edges."""
    successors: Dict[SimRunner, SuccessorInfo]
    """This simulator's successors in the dataflow graph and the
    corresponding edges."""
    triggering_ancestors: Iterable[Tuple[SimRunner, DenseTime]]
    """An iterable of this sim's ancestors that can trigger a step of
    this simulator. The second component specifies the least amount of
    time that output from the ancestor needs to reach us.
    """

    output_request: OutputRequest

    inputs_from_set_data: Dict
    """Inputs received via `set_data`."""
    persistent_inputs: Dict
    """Memory of previous inputs for persistent attributes."""
    timed_input_buffer: TimedInputBuffer
    """Inputs for this simulator."""

    output_to_push: Dict[Tuple[EntityId, Attr], List[Tuple[SimRunner, int, EntityId, Attr]]]
    """This lists those connections that use the timed_input_buffer.
    The keys are the entity-attribute pairs of this simulator with
    the corresponding list of simulator-time-entity-attribute triples
    describing the destinations for that data and the time-shift
    occuring along the connection.
    """

    progress: Progress[DenseTime]
    """This simulator's progress in mosaik time.

    This simulator has done all its work before time `progress`, so
    other simulator can rely on this simulator's output until this time.
    """
    last_step: DenseTime
    """The most recent step this simulator performed."""
    current_step: Optional[DenseTime]

    output_time: DenseTime
    """The output time associated with `data`. Usually, this will be equal to
    `last_step` but simulators may specify a different time for their output."""
    data: OutputData
    """The newest data returned by this simulator."""
    related_sims: Iterable[SimRunner]
    """Simulators related to this simulator. (Currently all other simulators.)"""
    task: asyncio.Task
    """The asyncio.Task for this simulator."""
    wait_events: List[asyncio.Event]
    """The list of all events for which this simulator is waiting"""
    rank: int
    """The topological rank of the simulator in the graph of all
    simulators with their non-weak, non-time-shifted connections.
    """

    outputs: Optional[Dict[Time, OutputData]]
    tqdm: tqdm.tqdm

    def __init__(
        self,
        sid: SimId,
        connection: Proxy,
    ):
        self.sid = sid
        self._proxy = connection

        self.type = connection.meta['type']
        self.supports_set_events = connection.meta.get('set_events', False)
        # Simulation state
        self.started = False
        self.last_step = DenseTime(-1)
        self.current_step = None
        if self.type != 'event-based':
            self.next_steps = [DenseTime(0)]
        else:
            self.next_steps = []
        self.next_self_step = None
        self.progress = Progress(DenseTime(0))
        self.inputs_from_set_data = {}
        self.persistent_inputs = {}
        self.timed_input_buffer = TimedInputBuffer()
        self.output_to_push = {}

        self.task = None  # type: ignore  # will be set in World.run
        self.newer_step = asyncio.Event()
        self.wait_events = []
        self.is_in_step = False
        self.rank = None  # type: ignore  # will be set in World.run

        self.predecessors = {}
        self.successors = {}

        self.output_request = {}

        self.outputs = None

    def schedule_step(self, dense_time: DenseTime):
        """Schedule a step for this simulator at the given time. This
        will trigger a re-evaluation whether this simulator's next
        step is settled, provided that the new step is earlier than the
        old one and the simulator is currently awaiting it's next
        settled step.
        """
        if dense_time in self.next_steps:
            return dense_time

        is_earlier = not self.next_steps or dense_time < self.next_steps[0]
        hq.heappush(self.next_steps, dense_time)
        if is_earlier:
            self.newer_step.set()

    async def setup_done(self):
        return await self._proxy.send(["setup_done", (), {}])

    async def step(self, time: Time, inputs: InputData, max_advance: Time) -> Optional[Time]:
        return await self._proxy.send(["step", (time, inputs, max_advance), {}])

    async def get_data(self, outputs: OutputRequest) -> OutputData:
        return await self._proxy.send(["get_data", (outputs,), {}])

    def get_output_for(self, time: Time):
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


class MosaikRemote:
    world: World
    sid: SimId

    def __init__(self, world: World, sid: SimId):
        self.world = world
        self.sid = sid

    @property
    def sim(self):
        return self.world.sims[self.sid]

    async def get_progress(self) -> float:
        """
        Return the current simulation progress from
        :attr:`~mosaik.scenario.World.sim_progress`.
        """
        return self.world.sim_progress

    async def get_related_entities(
        self,
        entities=None
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

        If *entities* is a single string (e.g., ``sid_1.eid_0``), return a dict
        containing all entities related to that entity::

            {
                'sid_0.eid_0': {'type': 'A'},
                'sid_0.eid_1': {'type': 'B'},
            }

        If *entities* is a list of entity IDs (e.g., ``['sid_0.eid_0',
        'sid_0.eid_1']``), return a dict mapping each entity to a dict of
        related entities::

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
            # repackage NodeViews and EdgeViews to maintain compatibility
            nodes_list = literal_eval(str(graph.nodes(data=True)))
            nodes_dict = dict({node[0]: node[1] for node in nodes_list})

            edges_list = literal_eval(str(graph.edges))
            edges_tuple = tuple(list(edge) + [{}] for edge in edges_list)

            return {'nodes': nodes_dict, 'edges': edges_tuple}
        elif type(entities) is str:
            return {n: graph.nodes[n] for n in graph[entities]}
        else:
            return {
                eid: {n: graph.nodes[n] for n in graph[eid]}
                for eid in entities
            }

    async def get_data(self, attrs) -> Dict[str, Any]:
        """
        Return the data for the requested attributes *attrs*.

        *attrs* is a dict of (fully qualified) entity IDs mapping to lists
        of attribute names (``{'sid/eid': ['attr1', 'attr2']}``).

        The return value is a dictionary, which maps the input entity IDs to
        data dictionaries, which in turn map attribute names to their
        respective values:
        (``{'sid/eid': {'attr1': val1, 'attr2': val2}}``).
        """
        assert self.sim.is_in_step, "get_data must happen in step"
        assert self.sim.current_step is not None, "no current step time"

        data = {}
        missing = collections.defaultdict(lambda: collections.defaultdict(list))
        dfg = self.world.df_graph
        dest_sid = self.sim.sid
        # Try to get data from cache
        for full_id, attr_names in attrs.items():
            sid, eid = full_id.split(FULL_ID_SEP, 1)
            # Check if async_requests are enabled.
            self._assert_async_requests(dfg, sid, dest_sid)
            if self.world.use_cache:
                cache_slice = self.world.sims[sid].get_output_for(self.sim.last_step)
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
            assert dep.progress.value > self.sim.current_step >= dep.last_step, \
                "sim progress wrong for async requests"
            dep_data = await dep._proxy.send(["get_data", (attrs,), {}])
            for eid, vals in dep_data.items():
                # Maybe there's already an entry for full_id, so we need
                # to update the dict in that case.
                data.setdefault(FULL_ID % (sid, eid), {}).update(vals)

        return data

    async def set_data(self, data):
        """
        Set *data* as input data for all affected simulators.

        *data* is a dictionary mapping source entity IDs to destination entity
        IDs with dictionaries of attributes and values (``{'src_full_id':
        {'dest_full_id': {'attr1': 'val1', 'attr2': 'val2'}}}``).
        """
        sims = self.world.sims
        dfg = self.world.df_graph
        dest_sid = self.sim.sid
        for src_full_id, dest in data.items():
            for full_id, attributes in dest.items():
                sid, eid = full_id.split(FULL_ID_SEP, 1)
                self._assert_async_requests(dfg, sid, dest_sid)
                inputs = sims[sid].inputs_from_set_data.setdefault(eid, {})
                for attr, val in attributes.items():
                    inputs.setdefault(attr, {})[src_full_id] = val

    async def set_event(self, event_time):
        """
        Schedules an event/step at simulation time *event_time*.
        """
        sim = self.world.sims[self.sid]
        if not self.world.rt_factor:
            raise SimulationError(
                f"Simulator '{self.sid}' tried to set an event in non-real-time "
                "mode."
            )
        if event_time < self.world.until:
            # TODO: Check whether progress.set is better
            # sim.progress.progress = min(event_time, sim.progress.progress)
            sim.schedule_step(event_time)
        else:
            logger.warning(
                "Event set at {event_time} by {sim_id} is after simulation end {until} "
                "and will be ignored.",
                event_time=event_time,
                sim_id=sim.sid,
                until=self.world.until,
            )

    def _assert_async_requests(self, dfg, src_sid, dest_sid):
        """
        Check if async. requests are allowed from *dest_sid* to *src_sid*
        and raise a :exc:`ScenarioError` if not.
        """
        data = {
            'src': src_sid,
            'dest': dest_sid,
        }
        if dest_sid not in dfg[src_sid]:
            raise ScenarioError(
                'No connection from "%(src)s" to "%(dest)s": You need to '
                'connect entities from both simulators and set '
                '"async_requests=True".' % data)
        if dfg[src_sid][dest_sid]['async_requests'] is not True:
            raise ScenarioError(
                'Async. requests not enabled for the connection from '
                '"%(src)s" to "%(dest)s". Add the argument '
                '"async_requests=True" to the connection of entities from '
                '"%(src)s" to "%(dest)s".' % data)


class StarterCollection(object):
    """
    This class provides a singleton instance of a collection of simulation
    starters. Default starters are:
    - python: start_inproc
    - cmd: start_proc
    - connect: start_connect

    External packages may add additional methods of starting simulations by
    adding new elements:

        from mosaik.simmanager import StarterCollection
        s = StarterCollection()
        s['my_starter'] = my_starter_func
    """

    # Singleton instance of the starter collection.
    __instance = None

    def __new__(cls) -> OrderedDict[str, Callable[..., Coroutine[Any, Any, BaseProxy]]]:
        if StarterCollection.__instance is None:
            # Create collection with default starters (i.e., starters defined
            # my mosaik core).
            StarterCollection.__instance = collections.OrderedDict(
                python=start_inproc,
                cmd=start_proc,
                connect=start_connect)

        return StarterCollection.__instance


class TimedInputBuffer:
    """
    A buffer to store inputs with its corresponding *time*.

    When the data is queried for a specific *step* time, all entries with
    *time* <= *step* are added to the input_dictionary.

    If there are several entries for the same connection at the same time, only
    the most recent value is added.
    """

    def __init__(self):
        self.input_queue = []
        self.counter = itertools.count()  # Used to chronologically sort entries

    def add(self, time, src_sid, src_eid, dest_eid, dest_var, value):
        src_full_id = '.'.join(map(str, (src_sid, src_eid)))
        hq.heappush(self.input_queue, (time, next(self.counter), src_full_id,
                                       dest_eid, dest_var, value))

    def get_input(self, input_dict, step):
        while len(self.input_queue) > 0 and self.input_queue[0][0] <= step:
            _, _, src_full_id, eid, attr, value = hq.heappop(self.input_queue)
            input_dict.setdefault(eid, {}).setdefault(attr, {})[
                src_full_id] = value

        return input_dict

    def __bool__(self):
        return bool(len(self.input_queue))
