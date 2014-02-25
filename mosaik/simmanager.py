"""
The simulation manager is responsible for starting simulation processes and
shutting them down.

It is able to start pure Python simulators in-process (by importing and
instantiating them), to start external simulation processes and to connect to
already running simulators and manage access to them.

"""
import collections
import importlib
import shlex
import subprocess
import types

from simpy.io.packet import PacketUTF8 as Packet
from simpy.io.json import JSON as JsonRpc

from mosaik.exceptions import ScenarioError


def start(env, sim_name, sim_id, sim_params):
    """Start the simulator *sim_name* based on the configuration im
    *env.sim_config*, give it the ID *sim_id* and pass the parameters of the
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
                'slots': 1,
            },
        }

    *ExampleSimA* is a pure Python simulator. Mosaik will import the module
    ``example_sim.mosaik`` and instantiate the class ``ExampleSim`` to start
    the simulator.

    *ExampleSimB* would be started by executing the command *example_sim* and
    passing the network address of mosaik das command line argument. You can
    optionally specify a *current working directory*. It defaults to ``.``.

    *ExampleSimC* can not be started by mosaik, so mosaik tries to connect to
    it. Only *slots* connections are allowed at the same time.

    The function returns a :class:`mosaik_api.Simulator` instance.

    It raises a :exc:`~mosaik.exceptions.SimulationError` if the simulator
    could not be started.

    Return a :class:`SimProxy` instance.

    """
    try:
        conf = env.sim_config[sim_name]
    except KeyError:
        raise ScenarioError('Simulator "%s" could not be started: Not found '
                            'in sim_config' % sim_name)

    # Try available starters in that order and raise an error if none of them
    # matches:
    starters = collections.OrderedDict(python=start_inproc,
                                       cmd=start_proc,
                                       connect=start_connect)
    for sim_type, start in starters.items():
        if sim_type in conf:
            return start(env, sim_name, conf, sim_id, sim_params)
    else:
        raise ScenarioError('Simulator "%s" could not be started: Invalid '
                            'configuration' % sim_name)


def start_inproc(env, sim_name, conf, sim_id, sim_params):
    """Import and instantiate the Python simulator *sim_name* based on its
    config entry *conf*.

    Raise a :exc:`~mosaik.exceptions.ScenarioError` if the simulator cannot be
    instantiated.

    """
    try:
        mod_name, cls_name = conf['python'].split(':')
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
    return InternalSimProxy(sim_id, sim, meta)


def start_proc(env, sim_name, conf, sim_id, sim_params):
    cmd = conf['cmd'] % {'addr': '%s:%s' % env.config['addr']}
    print(cmd)
    cmd = shlex.split(cmd)
    cwd = conf['cwd'] if 'cwd' in conf else '.'

    kwargs = {
        'bufsize': 1,
        'cwd': cwd,
        'universal_newlines': True,
    }
    try:
        proc = subprocess.Popen(cmd, **kwargs)
    except FileNotFoundError as e:
        raise ScenarioError('Simulator "%s" could not be started: %s' %
                            (sim_name, e.args[1]))

    def greeter():
        sock = yield env.srv_sock.accept()
        rpc_con = JsonRpc(Packet(sock))
        meta = yield rpc_con.remote.init(**sim_params)
        return ExternalSimProxy(sim_id, proc, rpc_con, meta)

    proxy = env.simpy_env.run(until=env.simpy_env.process(greeter()))
    return proxy


def start_connect(sim_name, conf, sim_id, sim_params):
    pass


class SimProxy:
    """Simple proxy/facade for in-process simulators."""
    def __init__(self, sid, meta):
        self.sid = sid
        self.meta = meta
        self.last_step = float('-inf')
        self.next_step = 0
        self.step_required = None

        # Bind proxy calls to API methods to this instance:
        remote_methods = ['create', 'step', 'get_data']
        for name in remote_methods:
            meth = types.MethodType(self._proxy_call(name), self)
            setattr(self, name, meth)

    def stop(self):
        return

    def _proxy_call(self, name):
        raise NotImplementedError


class InternalSimProxy(SimProxy):
    """Proxy for internal simulators."""
    def __init__(self, sid, inst, meta):
        self._inst = inst
        super().__init__(sid, meta)

    def _proxy_call(self, name):
        def meth(self, *args, **kwargs):
            return getattr(self._inst, name)(*args, **kwargs)
        meth.__name__ = name
        return meth


class ExternalSimProxy(SimProxy):
    """Proxy for external simulator processes."""
    def __init__(self, sid, proc, rpc_con, meta):
        self._proc = proc
        self._rpc_con = rpc_con
        super().__init__(sid, meta)

    def stop(self):
        # We don't want to yield the event, so we have to defuse it:
        evt = self._rpc_con.remote.stop()
        evt.defused = True

        self._rpc_con.close()
        self._proc.wait()

    def _proxy_call(self, name):
        def meth(self, *args, **kwargs):
            ret = yield getattr(self._remote, name)(*args, **kwargs)
            return ret
        meth.__name__ = name
        return meth
