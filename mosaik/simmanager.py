"""
The simulation manager is responsible for starting simulation processes and
shutting them down. It also manages the communication between mosaik and the
processes.

It is able to start pure Python simulators in-process (by importing and
instantiating them), to start external simulation processes and to connect to
already running simulators and manage access to them.

"""
import collections
import importlib
import shlex
import subprocess

from simpy.io import select as backend
from simpy.io.packet import PacketUTF8 as Packet
from simpy.io.json import JSON as JsonRpc
import mosaik_api

from mosaik.exceptions import ScenarioError
import mosaik


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
            if not is_valid_api_version(proxy.meta['api_version']):
                raise ScenarioError(
                    '"%s" API version %s is not compatible with mosaik '
                    'version %s.' % (sim_name, proxy.meta['api_version'],
                                     mosaik.__version__))
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
            ImportError: 'Could not import module',
            AttributeError: 'Class not found in module',
        }
        details = detail_msgs[type(err)]
        raise ScenarioError('Simulator "%s" could not be started: %s' %
                            (sim_name, details)) from None

    sim = cls()
    meta = sim.init(**sim_params)
    return LocalProcess(world, sim_id, sim, world.env, meta)


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

    proxy = world.env.run(until=world.env.process(greeter(
        world, sim_name, sim_config, sim_id, sim_params, proc=proc)))
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

    proxy = world.env.run(until=world.env.process(greeter(
        world, sim_name, sim_config, sim_id, sim_params, addr=addr)))
    return proxy


def greeter(world, sim_name, sim_config, sim_id, sim_params,
            proc=None, addr=None):
    """Try to establish a connection with *sim_name* and perform the ``init()``
    API call.

    Return a new :class:`RemoteProcess` sim proxy.

    Raise a :exc:`~mosaik.exceptions.ScenarioError` if something goes wrong.

    This method is a SimPy process used by :func:`start_proc()` and
    :func:`start_connect()`.

    """
    start_timeout = world.env.timeout(world.config['start_timeout'])
    if proc:
        # Wait for connection from "sim_name"
        accept_con = world.srv_sock.accept()
        results = yield accept_con | start_timeout
        if start_timeout in results:
            raise ScenarioError('Simulator "%s" did not connect to mosaik in '
                                'time.' % sim_name)
        else:
            sock = results[accept_con]
    else:
        # Connect to "sim_name"
        try:
            sock = backend.TCPSocket.connection(world.env, addr)
        except (ConnectionError, OSError):
            raise ScenarioError('Simulator "%s" could not be started: Could '
                                'not connect to "%s"' %
                                (sim_name, sim_config['connect']))

    rpc_con = JsonRpc(Packet(sock, max_packet_size=1024*1024))

    # Make init() API call and wait for sim_name's meta data.
    init = rpc_con.remote.init(**sim_params)
    results = yield init | start_timeout
    if start_timeout in results:
        raise ScenarioError('Simulator "%s" did not reply to the init() '
                            'call in time.' % sim_name)
    else:
        meta = results[init]

    return RemoteProcess(world, sim_id, proc, rpc_con, meta)


def is_valid_api_version(version):
    """Return ``True`` if the "major" part of *version* is the same as mosaik's
    version, else ``False``.

    """
    return int(version.split('.')[0]) == int(mosaik.__version__.split('.')[0])


class SimProxy:
    """Simple proxy/facade for in-process simulators."""
    def __init__(self, sid, meta):
        self.sid = sid
        self.meta = meta
        self.last_step = float('-inf')
        self.next_step = 0
        self.input_buffer = {}  # Buffer used by "MosaikRemote.set_data()"
        self.sim_proc = None  # SimPy process
        self.step_required = None  # SimPy event

        # Bind proxy calls to API methods to this instance. "init()" is missing
        # here, because it is called before the SimProxy is created
        remote_methods = ['create', 'step', 'get_data']
        for name in remote_methods:
            setattr(self, name, self._proxy_call(name))

    def stop(self):
        """Stop the simulator behind the proxy.

        The default implementation does nothing.

        """
        raise NotImplementedError

    def _proxy_call(self, name):
        raise NotImplementedError


class LocalProcess(SimProxy):
    """Proxy for internal simulators."""
    def __init__(self, world, sid, inst, env, meta):
        self._inst = inst
        self._env = env

        # Add MosaikRemote and patch its RPC methods to return events:
        inst.mosaik = MosaikRemote(world, sid)
        for attr in dir(inst.mosaik):
            if attr.startswith('_'):
                continue

            func = getattr(inst.mosaik, attr)
            if hasattr(func, '__call__') and hasattr(func, 'rpc'):
                setattr(inst.mosaik, attr, mosaik_api.get_wrapper(func, env))

        super().__init__(sid, meta)

    def stop(self):
        """Yield a triggered event but do nothing else."""
        yield self._env.event().succeed()

    def _proxy_call(self, name):
        """Return a wrapper method for the simulators method *name*.

        The wrapper method will return an event with the original return value
        as its value.

        """
        return mosaik_api.get_wrapper(getattr(self._inst, name), self._env)


class RemoteProcess(SimProxy):
    """Proxy for external simulator processes."""
    def __init__(self, world, sid, proc, rpc_con, meta):
        self._proc = proc
        self._rpc_con = rpc_con
        self._env = world.env
        self._mosaik_remote = MosaikRemote(world, sid)
        self._stop_timeout = world.config['stop_timeout']
        rpc_con.router = self._mosaik_remote.rpc
        super().__init__(sid, meta)

    def stop(self):
        """Send a *stop* message to the process represented by this proxy and
        wait for it to terminate.

        """
        try:
            yield (self._rpc_con.remote.stop() |
                   self._env.timeout(self._stop_timeout))
            print('Simulator "%s" did not close its connection in time.' %
                  self.sid)
            self._rpc_con.close()
        except ConnectionError:
            pass

        if self._proc:
            self._proc.wait()

    def _proxy_call(self, name):
        """Return the method *name* of the remote process."""
        return getattr(self._rpc_con.remote, name)


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
    def get_related_entities(self, entities):
        """Get a list of entities for *entities*.

        An *entity* may either be the string ``'sim_id/entity_id'`` or just
        ``'entity_id'``. If the latter is the case, use ``self.sim_id`` to
        identify the entiy.

        The return value is a dict mapping ``'sim_id/entity_id'`` to sorted
        lists of tuples ``('sim_id/entity_id', entity_type)``.

        """
        rels = {}
        entity_graph = self.world.entity_graph
        if type(entities) is not list:
            entities = [entities]

        for entity in entities:
            if '/' in entity:
                full_id = entity
            else:
                full_id = '%s/%s' % (self.sim_id, entity)

            rels[entity] = [
                (e, entity_graph.node[e]['entity'].type)
                for e in sorted(entity_graph[full_id])
            ]

        return rels

    @rpc.process
    def get_data(self, attrs):
        """Return the data for the requested attributes *attrs*.

        Attributes is a dict of (fully qualified) entity IDs mapping to lists
        of attribute names (``{'sid/eid': ['attr1', 'attr2']}``).

        The return value is a dict mapping the input entity IDs to data
        dictionaries mapping attribute names to there respective values.

        """
        sim = self.world.sims[self.sim_id]
        assert sim.next_step == sim.last_step  # Assert simulator is in step()
        cache_slice = self.world._df_cache[sim.last_step]

        data = {}
        missing = collections.defaultdict(
            lambda: collections.defaultdict(list))
        for full_id, attr_names in attrs.items():
            data[full_id] = {}
            sid, eid = full_id.split('/')
            for attr in attr_names:
                try:
                    data[full_id][attr] = cache_slice[sid][eid][attr]
                except KeyError:
                    missing[sid][eid].append(attr)

        for sid, attrs in missing.items():
            dep = self.world.sims[sid]
            assert (dep.next_step > sim.last_step and
                    dep.last_step <= sim.last_step)
            dep_data = yield dep.get_data(attrs)
            for eid, vals in dep_data.items():
                # Maybe there's already an entry for full_id, so we need
                # to update the dict in that case.
                data.setdefault('%s/%s' % (sid, eid), {}).update(vals)

        return data

    @rpc
    def set_data(self, data):
        """Set *data* as input data for all affected simulators.

        *data* is a dictionarry mapping *sim_id/entity_id* paths to
        dictionaries of attributes and values (``{'sid/eid': {'attr1': 'val1',
        'attr2': 'val2'}}``)

        """
        sims = self.world.sims
        for full_id, attributes in data.items():
            sid, eid = full_id.split('/', 1)
            inputs = sims[sid].input_buffer.setdefault(eid, {})
            for attr, val in attributes.items():
                # If multiple controlstrategies want to set the same attribute,
                # the last one wins and overwrites all previous values.
                inputs[attr] = [val]
