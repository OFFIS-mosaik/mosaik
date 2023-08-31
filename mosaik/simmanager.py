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
import platform
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

if 'Windows' in platform.system():
    from subprocess import CREATE_NEW_CONSOLE

from mosaik import _version
import mosaik_api_v3

from mosaik.exceptions import ScenarioError, SimulationError
from mosaik.proxies import LocalProxy, APIProxy, RemoteProxy

if TYPE_CHECKING:
    from mosaik.scenario import Meta, OutputData, SimId, World, DataflowEdge

FULL_ID_SEP = '.'  # Separator for full entity IDs
FULL_ID = '%s.%s'  # Template for full entity IDs ('sid.eid')


async def start(
    world: World,
    sim_name: str,
    sim_id: SimId,
    time_resolution: float,
    sim_params: Dict[str, Any],
):
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

    The function returns a :class:`mosaik_api_v3.Simulator` instance.

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
                await asyncio.wait_for(
                    proxy.init(sim_id, time_resolution=time_resolution, **sim_params),
                    world.config['start_timeout']
                )
                return SimRunner(sim_name, sim_id, world, proxy)
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
) -> APIProxy:
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
        }
        details = detail_msgs[type(err)]
        origerr = err.args[0]
        raise ScenarioError('Simulator "%s" could not be started: %s --> %s' %
                            (sim_name, details, origerr)) from None
    sim = cls()

    if int(mosaik_api_v3.__version__.split('.')[0]) < 3:
        raise ScenarioError("Mosaik 3 requires mosaik_api_v3 or newer.")

    return LocalProxy(mosaik_remote, sim)


async def start_proc(
    world: World,
    sim_name: str,
    sim_config: Dict[Literal["cmd", "cwd", "env", "posix", "new_console"], Any],
    mosaik_remote: MosaikRemote,
) -> APIProxy:
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
        cmd = shlex.split(cmd, posix=posix)
    else:
        cmd = shlex.split(cmd, posix=(os.name != 'nt'))
    cwd = sim_config['cwd'] if 'cwd' in sim_config else '.'

    # Make a copy of the current env. vars dictionary and update it with the
    # user provided values (or an empty dict as a default):
    env = dict(os.environ)
    env.update(sim_config.get('env', {}))  # type: ignore

    # CREATE_NEW_CONSOLE constant for subprocess is only available on Windows
    creationflags = 0
    new_console = sim_config['new_console'] if 'new_console' in sim_config else False
    if new_console:
        if 'Windows' in platform.system():
            creationflags = CREATE_NEW_CONSOLE
        else:
            logger.warning('Simulator "{sim_name}" could not be started in a new console: '
                           'Only available on Windows', sim_name=sim_name)

    kwargs = {
        'bufsize': 1,
        'cwd': cwd,
        'universal_newlines': True,
        'env': env,  # pass the new env dict to the sub process
        'creationflags': creationflags,
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
        (reader, writer) = await asyncio.wait_for(
            world.incoming_connections_queue.get(),
            world.config['start_timeout'],
        )
        return RemoteProxy(mosaik_remote, reader, writer)
    except asyncio.TimeoutError:
        raise SimulationError(
            f'Simulator "{sim_name}" did not connect to mosaik in time.'
        )


async def start_connect(
    world: World,
    sim_name: str,
    sim_config,
    mosaik_remote: MosaikRemote,
) -> APIProxy:
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
    return RemoteProxy(mosaik_remote, reader, writer)


class SimRunner:
    """
    Handler for an external simulator.

    It stores its simulation state and own the proxy object to the external
    simulator.
    """

    name: str
    """The name of this simulator (in the SIM_CONFIG)."""
    sid: SimId
    """This simulator's ID."""
    meta: Meta
    """This simulator's meta."""
    type: Literal['time-based', 'event-based', 'hybrid']

    proxy: APIProxy
    """The actual proxy for this simulator."""

    rt_start: float
    """The real time when this simulator started (as returned by
    `perf_counter()`."""
    started: bool

    next_steps: List[int]
    """The scheduled next steps this simulator will take, organized as a heap.
    Once the immediate next step has been chosen (and the `has_next_step` event
    has been triggered), the step is moved to `next_step` instead."""
    next_step: Optional[int]
    """This simulator's immediate next step once it has been determined. The
    step is removed from the `next_steps` heap at that point and the
    `has_next_step` event is triggered."""
    has_next_step: asyncio.Event
    """An event that is triggered once this simulator's next step has been
    determined."""
    next_self_step: Optional[int]
    """The next self-scheduled step for this simulator."""
    interruptable: bool
    """Set when this simulator's next step has been scheduled but it is still
    waiting for dependencies which might trigger earlier steps for this
    simulator."""

    predecessors: Dict[Any, Tuple[SimRunner, DataflowEdge]]
    """This simulator's predecessors in the dataflow graph and the corresponding
    edges."""
    successors: Dict[Any, Tuple[SimRunner, DataflowEdge]]
    """This simulator's successors in the dataflow graph and the corresponding
    edge.."""
    triggering_ancestors: Iterable[Tuple[SimId, bool]]
    """
    An iterable of this sim's ancestors that can trigger a step of this
    simulator. The second component specifies whether the connecting is weak or
    time-shifted (False) or immediate (True).
    """

    input_buffer: Dict
    """Inputs received via `set_data`."""
    input_memory: Dict
    """Memory of previous inputs for persistent attributes."""
    timed_input_buffer: TimedInputBuffer
    """'Usual' inputs. (But also see `world._df_cache`.)"""

    progress: int
    """This simulator's progress in mosaik time.

    This simulator has done all its work before time `progress`; its next stept will be
    at time `progress` or later. For time-based simulators, the next step will happen
    at time `progress`."""
    last_step: int
    """The most recent step this simulator performed."""

    output_time: int
    """The output time associated with `data`. Usually, this will be equal to
    `last_step` but simulators may specify a different time for their output."""
    data: OutputData
    """The newest data returned by this simulator."""
    related_sims: Iterable[SimRunner]
    """Simulators related to this simulator. (Currently all other simulators.)"""
    sim_proc: asyncio.Task
    """The asyncio.Task for this simulator."""
    wait_events: List[asyncio.Event]
    """The event (usually an AllOf event) this simulator is waiting for."""
    trigger_cycles: List[TriggerCycle]
    """Triggering cycles in a simulation"""

    def __init__(
        self,
        name: str,
        sid: SimId,
        world: World,
        proxy: APIProxy,
    ):
        self.name = name
        self.sid = sid
        self._world = world
        self.proxy = proxy

        self.type = proxy.meta.get('type', 'time-based')
        # Simulation state
        self.started = False
        self.last_step = -1
        if self.type != 'event-based':
            self.next_steps = [0]
        else:
            self.next_steps = []
        self.next_self_step = None
        self.progress = 0
        self.input_buffer = {}  # Buffer used by "MosaikRemote.set_data()"
        self.input_memory = {}
        self.timed_input_buffer = TimedInputBuffer()
        self.buffered_output = {}
        self.sim_proc = None  # type: ignore  # will be set in Mosaik's init
        self.has_next_step = asyncio.Event()
        self.wait_events = []
        self.interruptable = False
        self.is_in_step = False
        self.trigger_cycles = []
        self.rank = None  # topological rank

    def schedule_step(self, time: int):
        """Schedule a step for this simulator at the given time. This will wake this
        simulator and if the new step is earlier than previously scheduled steps, the
        sim_process will be interrupted with an 'Earlier step' message."""
        if time in self.next_steps:
            return

        is_earlier = self.next_steps and time < self.next_steps[0]
        hq.heappush(self.next_steps, time)
        self.has_next_step.set()
        if is_earlier and self.interruptable:
            self.sim_proc.cancel()

    async def stop(self):
        """
        Stop the simulator behind the proxy.
        """
        await self.proxy.stop()


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
        assert self.sim.is_in_step
        cache_slice = (
            self.world._df_cache[self.sim.last_step]
            if self.world._df_cache is not None
            else {}
        )

        data = {}
        missing = collections.defaultdict(
            lambda: collections.defaultdict(list))
        dfg = self.world.df_graph
        dest_sid = self.sim.sid
        # Try to get data from cache
        for full_id, attr_names in attrs.items():
            sid, eid = full_id.split(FULL_ID_SEP, 1)
            # Check if async_requests are enabled.
            self._assert_async_requests(dfg, sid, dest_sid)

            data[full_id] = {}
            for attr in attr_names:
                try:
                    data[full_id][attr] = cache_slice[sid][eid][attr]
                except KeyError:
                    missing[sid][eid].append(attr)

        # Query simulator for data not in the cache
        for sid, attrs in missing.items():
            dep = self.world.sims[sid]
            assert (dep.progress > self.sim.last_step >= dep.last_step)
            dep_data = await dep.proxy.get_data(attrs)
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
                inputs = sims[sid].input_buffer.setdefault(eid, {})
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
            sim.progress = min(event_time, sim.progress)
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

    def __new__(cls) -> OrderedDict[str, Callable[..., Coroutine[Any, Any, APIProxy]]]:
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


@dataclass
class TriggerCycle:
    """
    Stores the information of triggering cycles of a simulator
    """

    sids: List[SimId]
    activators: Set[Tuple[str, str]]
    """List of all attributes that trigger the destination simulator if the given edge"""
    min_length: int
    """
    If connections between simulators are time-shifted, the cycle needs more time for
    a trigger round. If no edge is timeshifted, the minimum length is 0.
    """
    in_edge: DataflowEdge
    """The edge that is going into the simulator"""
    time: int
    count: int
