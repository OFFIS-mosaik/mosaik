"""
The simulation manager is responsible for starting simulation processes and
shutting them down. It also manages the communication between mosaik and the
processes.

It is able to start pure Python simulators in-process (by importing and
instantiating them), to start external simulation processes and to connect to
already running simulators and manage access to them.

"""
import collections
import copy
import importlib
import shlex
import subprocess

from simpy.io import select as backend
from simpy.io.packet import PacketUTF8 as Packet
from simpy.io.json import JSON as JsonRpc
import mosaik_api

from mosaik.exceptions import ScenarioError, SimulationError
from mosaik.util import sync_process


API_VERSION = 2  # Current version of the simulator API
FULL_ID_SEP = '.'  # Separator for full entity IDs
FULL_ID = '%s.%s'  # Template for full entity IDs ('sid.eid')


def start(world, sim_name, sim_id, sim_params):
    """Start the simulator *sim_name* based on the configuration im
    *world.sim_config*, give it the ID *sim_id* and pass the parameters of the
    dict *sim_params* to it.

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
    # matches:
    starters = collections.OrderedDict(python=start_inproc,
                                       cmd=start_proc,
                                       connect=start_connect)
    for sim_type, start in starters.items():
        if sim_type in sim_config:
            proxy = start(world, sim_name, sim_config, sim_id, sim_params)
            if not valid_api_version(proxy.meta['api_version'], API_VERSION):
                raise ScenarioError(
                    '"%s" API version %s is not compatible with mosaik '
                    'version %s.' % (sim_name, proxy.meta['api_version'],
                                     API_VERSION))
            return proxy
    else:
        raise ScenarioError('Simulator "%s" could not be started: Invalid '
                            'configuration' % sim_name)


def start_inproc(world, sim_name, sim_config, sim_id, sim_params):
    """Import and instantiate the Python simulator *sim_name* based on its
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
            ImportError: 'Could not import module: %s' % err.args[0],
            AttributeError: 'Class not found in module',
        }
        details = detail_msgs[type(err)]
        raise ScenarioError('Simulator "%s" could not be started: %s' %
                            (sim_name, details)) from None

    sim = cls()
    meta = sim.init(sim_id, **sim_params)
    # "meta" is module global and thus shared between all "LocalProcess"
    # instances. This may leed to problems if a user modfies it, so make
    # a deep copy of it for each instance:
    meta = copy.deepcopy(meta)
    return LocalProcess(sim_name, sim_id, meta, sim, world)


def start_proc(world, sim_name, sim_config, sim_id, sim_params):
    """Start a new process for simulator *sim_name* based on its config entry
    *sim_config*.

    Return a :class:`RemoteProcess` instance.

    Raise a :exc:`~mosaik.exceptions.ScenarioError` if the simulator cannot be
    instantiated.

    """
    cmd = sim_config['cmd'] % {'addr': '%s:%s' % world.config['addr']}
    cmd = shlex.split(cmd)
    cwd = sim_config['cwd'] if 'cwd' in sim_config else '.'

    kwargs = {
        'bufsize': 1,
        'cwd': cwd,
        'universal_newlines': True,
    }
    try:
        proc = subprocess.Popen(cmd, **kwargs)
    except (FileNotFoundError, NotADirectoryError) as e:
        raise ScenarioError('Simulator "%s" could not be started: %s' %
                            (sim_name, e.args[1])) from None

    proxy = make_proxy(world, sim_name, sim_config, sim_id, sim_params,
                       proc=proc)
    return proxy


def start_connect(world, sim_name, sim_config, sim_id, sim_params):
    """Connect to the already running simulator *sim_name* based on its config
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
        raise ScenarioError('Simulator "%s" could not be started: Could not '
                            'parse address "%s"' %
                            (sim_name, sim_config['connect'])) from None

    proxy = make_proxy(world, sim_name, sim_config, sim_id, sim_params,
                       addr=addr)
    return proxy


def make_proxy(world, sim_name, sim_config, sim_id, sim_params,
               proc=None, addr=None):
    """Try to establish a connection with *sim_name* and perform the ``init()``
    API call.

    Return a new :class:`RemoteProcess` sim proxy.

    Raise a :exc:`~mosaik.exceptions.ScenarioError` if something goes wrong.

    This method is a SimPy process used by :func:`start_proc()` and
    :func:`start_connect()`.

    """
    start_timeout = world.env.timeout(world.config['start_timeout'])

    def greeter():
        if proc:
            # Wait for connection from "sim_name"
            accept_con = world.srv_sock.accept()
            results = yield accept_con | start_timeout
            if start_timeout in results:
                raise SimulationError('Simulator "%s" did not connect to '
                                      'mosaik in time.' % sim_name)
            else:
                sock = results[accept_con]
        else:
            # Connect to "sim_name"
            try:
                sock = backend.TCPSocket.connection(world.env, addr)
            except (ConnectionError, OSError):
                raise SimulationError('Simulator "%s" could not be started: '
                                      'Could not connect to "%s"' %
                                      (sim_name, sim_config['connect']))

        rpc_con = JsonRpc(Packet(sock, max_packet_size=10*1024*1024))

        # Make init() API call and wait for sim_name's meta data.
        init = rpc_con.remote.init(sim_id, **sim_params)
        try:
            results = yield init | start_timeout
        except ConnectionError as e:
            raise SimulationError('Simulator "%s" closed its connection during'
                                  ' the init() call.' % sim_name, e)

        if start_timeout in results:
            raise SimulationError('Simulator "%s" did not reply to the init() '
                                  'call in time.' % sim_name)
        else:
            meta = results[init]

        return RemoteProcess(sim_name, sim_id, meta, proc, rpc_con, world)

    return sync_process(greeter(), world)


def valid_api_version(simulator_version, expected_version):
    """REturn ``True`` if the *simulator_version* equals the
    *expected_version*, else ``False``."""
    return simulator_version == expected_version


class SimProxy:
    """Handler for an external simulator.

    It stores its simulation state and own the proxy object to the external
    simulator.

    """
    def __init__(self, name, sid, meta, world):
        self.name = name
        self.sid = sid
        self.meta = meta
        self._world = world

        # Meta data and remote method checks
        api_methods = [
            # "init" was called before the SimProxy was created
            'create',
            'step',
            'get_data',
        ]
        # Set default value for optional "extra_methods" property
        extra_methods = meta.setdefault('extra_methods', [])

        self._check_model_and_meth_names(meta['models'], api_methods,
                                         extra_methods)

        # Set default value for optional "any_inputs" property
        for model, props in meta['models'].items():
            props.setdefault('any_inputs', False)

        # Actual proxy object
        self.proxy = self._get_proxy(api_methods + extra_methods)

        # Simulation state
        self.last_step = -1
        self.next_step = 0
        self.input_buffer = {}  # Buffer used by "MosaikRemote.set_data()"
        self.sim_proc = None  # SimPy process
        self.step_required = None  # SimPy event

    def stop(self):
        """Stop the simulator behind the proxy.

        The default implementation does nothing.

        """
        raise NotImplementedError

    def _get_proxy(self, methods):
        raise NotImplementedError

    def _check_model_and_meth_names(self, models, api_methods, extra_methods):
        """Check if there are any overlaps in model names and reserved API
        methods as well as in them and extra API methods.

        Raise a :exc:`~mosaik.exception.ScenarioError` if that's the case.

        """
        models = list(models)
        illegal_models = set(models) & set(api_methods)
        if illegal_models:
            raise ScenarioError('Simulator "%s" uses illegal model names: %s' %
                                (self.sid, ', '.join(illegal_models)))

        illegal_meths = set(models + api_methods) & set(extra_methods)
        if illegal_meths:
            raise ScenarioError('Simulator "%s" uses illegal extra method '
                                'names: %s' %
                                (self.sid, ', '.join(illegal_meths)))


class LocalProcess(SimProxy):
    """Proxy for internal simulators."""
    def __init__(self, name, sid, meta, inst, world):
        self._inst = inst

        # Add MosaikRemote and patch its RPC methods to return events:
        inst.mosaik = MosaikRemote(world, sid)
        for attr in dir(inst.mosaik):
            if attr.startswith('_'):
                continue

            func = getattr(inst.mosaik, attr)
            if hasattr(func, '__call__') and hasattr(func, 'rpc'):
                setattr(inst.mosaik, attr,
                        mosaik_api.get_wrapper(func, world.env))

        super().__init__(name, sid, meta, world)

    def stop(self):
        """Yield a triggered event but do nothing else."""
        self._inst.finalize()
        yield self._world.env.event().succeed()

    def _get_proxy(self, methods):
        """Return a proxy for the local simulator."""
        proxy_dict = {
            name: mosaik_api.get_wrapper(getattr(self._inst, name),
                                         self._world.env)
            for name in methods
        }
        Proxy = type('Proxy', (), proxy_dict)
        return Proxy


class RemoteProcess(SimProxy):
    """Proxy for external simulator processes."""
    def __init__(self, name, sid, meta, proc, rpc_con, world):
        self._proc = proc
        self._rpc_con = rpc_con
        self._mosaik_remote = MosaikRemote(world, sid)
        self._stop_timeout = world.config['stop_timeout']
        rpc_con.router = self._mosaik_remote.rpc
        super().__init__(name, sid, meta, world)

    def stop(self):
        """Send a *stop* message to the process represented by this proxy and
        wait for it to terminate.

        """
        try:
            timeout = self._world.env.timeout(self._stop_timeout)
            res = yield (self._rpc_con.remote.stop() | timeout)
            if timeout in res:
                print('Simulator "%s" did not close its connection in time.' %
                      self.sid)
                self._rpc_con.close()
        except ConnectionError:
            # We may get a ConnectionError if the remote site closes its
            # socket during the "stop()" call.
            pass

        if self._proc:
            self._proc.wait()

    def _get_proxy(self, methods):
        """Return a proxy object for the remote simulator."""
        return self._rpc_con.remote


class MosaikRemote:
    """This class provides an RPC interface for remote processes to query
    mosaik and other processes (simulators) for data while they are executing
    a ``step()`` command.

    """
    @JsonRpc.Descriptor
    class rpc(JsonRpc.Accessor):
        parent = None

    def __init__(self, world, sim_id):
        self.world = world
        self.sim_id = sim_id

    @rpc
    def get_progress(self):
        """Return the current simulation progress from
        :attr:`~mosaik.scenario.World.sim_progress`.

        """
        return self.world.sim_progress

    @rpc
    def get_related_entities(self, entities=None):
        """Return information about the related entities of *entities*.

        If *entitites* omitted (or ``None``), return the complete entity
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
        eg = self.world.entity_graph
        if entities is None:
            return {'nodes': eg.node, 'edges': eg.edges(data=True)}
        elif type(entities) is str:
            return {n: eg.node[n] for n in eg[entities]}
        else:
            return {
                eid: {n: eg.node[n] for n in eg[eid]}
                for eid in entities
            }

    @rpc.process
    def get_data(self, attrs):
        """Return the data for the requested attributes *attrs*.

        *attrs* is a dict of (fully qualified) entity IDs mapping to lists
        of attribute names (``{'sid/eid': ['attr1', 'attr2']}``).

        The return value is a dict mapping the input entity IDs to data
        dictionaries mapping attribute names to there respective values
        (``{'sid/eid': {'attr1': val1, 'attr2': val2}}``).

        """
        sim = self.world.sims[self.sim_id]
        assert sim.next_step == sim.last_step  # Assert simulator is in step()
        cache_slice = self.world._df_cache[sim.last_step]

        data = {}
        missing = collections.defaultdict(
            lambda: collections.defaultdict(list))
        dfg = self.world.df_graph
        dest_sid = self.sim_id
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
            assert (dep.next_step > sim.last_step and
                    dep.last_step <= sim.last_step)
            dep_data = yield dep.proxy.get_data(attrs)
            for eid, vals in dep_data.items():
                # Maybe there's already an entry for full_id, so we need
                # to update the dict in that case.
                data.setdefault(FULL_ID % (sid, eid), {}).update(vals)

        return data

    @rpc
    def set_data(self, data):
        """Set *data* as input data for all affected simulators.

        *data* is a dictionary mapping source entity IDs to destination entity
        IDs with dictionaries of attributes and values (``{'src_full_id':
        {'dest_full_id': {'attr1': 'val1', 'attr2': 'val2'}}}``).

        """
        sims = self.world.sims
        dfg = self.world.df_graph
        dest_sid = self.sim_id
        for src_full_id, dest in data.items():
            for full_id, attributes in dest.items():
                sid, eid = full_id.split(FULL_ID_SEP, 1)
                self._assert_async_requests(dfg, sid, dest_sid)
                inputs = sims[sid].input_buffer.setdefault(eid, {})
                for attr, val in attributes.items():
                    inputs.setdefault(attr, {})[src_full_id] = val

    def _assert_async_requests(self, dfg, src_sid, dest_sid):
        """Check if async. requests are allowed from *dest_sid* to *src_sid*
        and raise a :exc:`ScenarioError` if not."""
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
