"""
Mosaik API for simulations written in Python.

"""
import inspect
import logging
import re
import socket
import sys
import traceback

from simpy._compat import PY2
from simpy.io import select as backend
from simpy.io.packet import PacketUTF8 as Packet
from simpy.io.message import Message
import docopt


if PY2:
    ConnectionError = socket.error
    ConnectionRefusedError = socket.error

__version__ = '2.4'
__api_version__ = __version__
logger = logging.getLogger('mosaik_api')

_HELP = """%(desc)s

Usage:
    %(prog)s [options] HOST:PORT

Options:
    HOST:PORT   Connect to this address
    -l LEVEL, --log-level LEVEL
                Log level for simulator (%(levels)s) [default: info]
    -r, --remote
                Simulator is to be started on a machine remote from mosaik
    -t TIME, --timeout TIME
                Timeout in seconds for mosaik handshake [default: 60]
%(extra_opts)s
"""
_LOG_LEVELS = {
    'debug': logging.DEBUG,
    'info': logging.INFO,
    'warning': logging.WARNING,
    'error': logging.ERROR,
    'critical': logging.CRITICAL,
}


# NOTE: We don't use an ABC here, because the effort of making it py2 AND py3
# compatible (-> meta classes) outweighs the benefits.
class Simulator(object):
    """This is the base class that you need to inherit from and implement the
    API calls."""

    meta = None
    """Meta data describing the simulator (the same that is returned by
    :meth:`init()`).

    ::

        {
            'api_version': 'x.y',
            'models': {
                'ModelName': {
                    'public': True|False,
                    'params': ['param_1', ...],
                    'attrs': ['attr_1', ...],
                    'any_inputs': True|False,
                },
                ...
            },
            'extra_methods': [
                'do_cool_stuff',
                'set_static_data'
            ]
        }

    The *api_version* is a string that defines which version of the mosaik API
    the simulator implements.  Since mosaik API version 2.3, the simulator's
    `major version <http://semver.org/>`_ ("x", in the snippet above) has to be
    equal to mosaik's.  Mosaik will cancel the simulation if a version mismatch
    occurs.

    *models* is a dictionary describing the models provided by this simulator.
    The entry *public* determines whether a model can be instantiated by a user
    (``True``) or if it is a sub-model that cannot be created directly
    (``False``). *params* is a list of parameter names that can be passed to
    the model when creating it. *attrs* is a list of attribute names that can
    be accessed (reading or writing).  If the optional *any_inputs* flag is set
    to ``true``, any attributes can be connected to the model, even if they are
    not *attrs*. This may, for example, be useful for databases that don't know
    in advance which attributes of an entity they'll receive.


    *extra_methods* is an optional list of methods that a simulator provides in
    addition to the standard API calls (``init()``, ``create()`` and so on).
    These methods can be called while the scenario is being created and can be
    used for operations that don't really belong into ``init()`` or
    ``create()``.

    """

    mosaik = None  # Will be set by "start_simulation()"
    """An RPC proxy to mosaik."""

    def __init__(self, meta):
        self.meta = {
            'api_version': __api_version__,
            'models': {},
        }
        self.meta.update(meta)

    def init(self, sid, **sim_params):
        """Initialize the simulator with the ID *sid* and apply additional
        parameters *(sim_params)* sent by mosaik. Return the meta data
        :attr:`meta`.

        If your simulator has no *sim_params*, you don't need to override this
        method.

        """
        return self.meta

    def create(self, num, model, **model_params):
        """Create *num* instances of *model* using the provided *model_params*.

        *num* is an integer for the number of model instances to create.

        *model* needs to be a public entry in the simulator's
        ``meta['models']``.

        *model_params* is a dictionary mapping parameters (from
        ``meta['models'][model]['params']``) to their values.

        Return a (nested) list of dictionaries describing the created model
        instances (entities). The root list must contain exactly *num*
        elements. The number of objects in sub-lists is not constrained::

            [
                {
                    'eid': 'eid_1',
                    'type': 'model_name',
                    'rel': ['eid_2', ...],
                    'children': [
                        {'eid': 'child_1', 'type': 'child'},
                        ...
                    ],
                },
                ...
            ]

        The entity ID (*eid*) of an object must be unique within a simulator
        instance. For entities in the root list, *type* must be the same as the
        *model* parameter. The type for objects in sub-lists may be anything
        that can be found in ``meta['models']``. *rel* is an optional list of
        related entities; "related" means that two entities are somehow connect
        within the simulator, either logically or via a real data-flow (e.g.,
        grid nodes are related to their adjacent branches). The *children*
        entry is optional and may contain a sub-list of entities.

        """
        raise NotImplementedError

    def setup_done(self):
        """Callback that indicates that the scenario setup is done and the
        actual simulation is about to start.

        At this point, all entities and all connections between them are know
        but no simulator has been stepped yet.

        Implementing this method is optional.

        *Added in mosaik API version 2.3*

        """

    def step(self, time, inputs):
        """Perform the next simulation step from time *time* using input values
        from *inputs* and return the new simulation time (the time at which
        ``step()`` should be called again).

        *time* and the time returned are integers. Their unit is arbitrary,
        e.g. *seconds* (from simulation start), but has to be consistent among
        all simulators used in a simulation.

        *inputs* is a dict of dicts mapping entity IDs to attributes and
        dicts of values (each simulator has do decide on its own how to reduce
        the values (e.g., as its sum, average or maximum)::

            {
                'dest_eid': {
                    'attr': {'src_fullid': val, ...},
                    ...
                },
                ...
            }

        """
        raise NotImplementedError

    def get_data(self, outputs):
        """Return the data for the requested attributes in *outputs*

        *outputs* is a dict mapping entity IDs to lists of attribute names
        whose values are requested::

            {
                'eid_1': ['attr_1', 'attr_2', ...],
                ...
            }

        The return value needs to be a dict of dicts mapping entity IDs and
        attribute names to their values::

            {
                'eid_1: {
                    'attr_1': 'val_1',
                    'attr_2': 'val_2',
                    ...
                },
                ...
            }

        """
        raise NotImplementedError

    def configure(self, args, backend, env):
        """This method can be overridden to configure the simulation with the
        command line *args* as created by `docopt <http://docopt.org/>`_.

        *backend* and *env* are the *simpy.io* backend and environment used
        for networking. You can use them to start extra processes (e.g., a
        web server).

        The default implementation simply ignores them.

        """
        pass

    def event_setter(self, args, sock, env):
        pass

    def finalize(self):
        """This method can be overridden to do some clean-up operations after
        the simulation finished (e.g., shutting down external processes).

        """
        pass


class MosaikProxy(object):
    exposed_meths = [
        'get_progress',
        'get_related_entities',
        'get_data',
        'set_data',
    ]

    def __init__(self, channel):
        self._channel = channel

    def __getattr__(self, name):
        if name not in MosaikProxy.exposed_meths:
            raise AttributeError

        def proxy_call(*args, **kwargs):
            return self._channel.send([name, args, kwargs])

        return proxy_call


def start_simulation(simulator, description='', extra_options=None):
    """Start the simulation process for ``simulation``.

    *simulation* is the instance of your API implementation (see
    :class:`Simulator`).

    *description* may override the default description printed with the help on
    the command line.

    *extra_option* may be a list of options for `docopt <http://docopt.org/>`_
    (example: ``['-e, --example     Enable example mode']``). Commandline
    arguments are passed to :meth:`Simulator.configure()` so that your API
    implementation can handle them.

    """
    OK, ERR = 0, 1

    args = _parse_args(description or 'Start the simulation service.',
                       extra_options or [])

    logging.basicConfig(level=args['--log-level'])
    remote_flag = args['--remote'] if '--remote' in args.keys() else False
    sim_name = simulator.__class__.__name__

    sock = None
    srv_sock = None
    try:
        logger.info('Starting %s ...' % sim_name)
        env = backend.Environment()
        simulator.configure(args, backend, env)

        # Setup simpy.io and start the event loop.
        addr = _parse_addr(args['HOST:PORT'])
        # Interception for remote simulators
        if remote_flag:
            srv_sock = backend.TCPSocket.server(env, addr)
            start_timeout = env.timeout(int(args['--timeout']))
            def greeter():
                """ Handshake with mosaik to establish a socket for communication """
                logger.info('Waiting for connection from mosaik')
                accept_con = srv_sock.accept()
                results = yield accept_con | start_timeout
                if start_timeout in results:
                    raise RuntimeError('Connection from mosaik not received in time')
                else:
                    sock = results[accept_con]
                return sock
            sock = env.run(until=env.process(greeter()))
        else:
            sock = backend.TCPSocket.connection(env, addr)
        sock = Message(env, Packet(sock, max_packet_size=10*1024*1024))
        simulator.mosaik = MosaikProxy(sock)
        proc = env.process(init(sock, simulator))
        env.run(until=proc)
        proc = env.process(run(sock, simulator))
        env.process(simulator.event_setter(env, sock))
        env.run(until=proc)
    except ConnectionRefusedError:
        logger.error('Could not connect to mosaik.')
        errstr = 'INFO:mosaik_api:Starting ExampleSim ...\n' + 'ERROR:mosaik_api:Could not connect to mosaik.\n'
        return errstr
    except (ConnectionError, KeyboardInterrupt):
        pass  # Exit silently.
    except Exception as exc:
        if type(exc) is OSError and exc.errno == 10057:
            # ConnectionRefusedError in Windows O.o
            logger.error('Could not connect to mosaik.')
            return ERR

        print('Error in %s:' % sim_name)
        traceback.print_exc()  # Exit loudly
        print('---------%s-' % ('-' * len(sim_name)))
        return ERR
    finally:
        if sock is not None:
            sock.close()
        if srv_sock is not None:
            srv_sock.close()
        simulator.finalize()

    return OK


def init(channel, sim):
    init_func = get_wrapper(sim.init, channel.env)
    request = yield channel.recv()
    func, args, kwargs = request.content
    logger.debug('Calling %s(*%s, **%s)' % (func, args, kwargs))
    assert func == 'init'
    ret = yield init_func(*args, **kwargs)
    request.succeed(ret)


def run(channel, sim):
    """Main simulator process. Send a greeting message to mosaik and wait
    for requests to step the simulation, get data or whatever.

    *channel* is a :class:`simpy.io.message.Message` instance.

    *sim* is the instance of an :class:`Simulator` implementation.

    """
    funcs = {
        'init': sim.init,
        'create': sim.create,
        'setup_done': sim.setup_done,
        'step': sim.step,
        'get_data': sim.get_data,
    }
    extra_funcs = {
        name: getattr(sim, name) for name in sim.meta.get('extra_methods', [])
    }
    funcs.update(extra_funcs)
    for name, func in funcs.items():
        funcs[name] = get_wrapper(func, channel.env)

    logger.debug('Entering event loop ...')
    while True:
        request = yield channel.recv()
        func, args, kwargs = request.content
        logger.debug('Calling %s(*%s, **%s)' % (func, args, kwargs))
        if func == 'stop':
            break

        func = funcs[func]
        ret = yield func(*args, **kwargs)
        request.succeed(ret)


def get_wrapper(func, env):
    if inspect.isgeneratorfunction(func):
        def wrapper(*args, **kwargs):
            return env.process(func(*args, **kwargs))
    else:
        def wrapper(*args, **kwargs):
            ret = func(*args, **kwargs)
            return env.event().succeed(ret)
    wrapper.__name__ = func.__name__
    return wrapper


def _parse_args(desc, extra_options):
    """Fill-in the values into :data:`_HELP` and parse and return the arguments
    using :func:`~docopt.docopt()`.

    """
    log_levels = (l[0] for l in sorted(_LOG_LEVELS.items(),
                                       key=lambda l: l[1]))
    msg = _HELP % {
        'desc': desc,
        'prog': sys.argv[0],
        'levels': ', '.join(log_levels),
        'extra_opts': '\n'.join('    %s' % opt
                                for opt in extra_options),
    }
    args = docopt.docopt(msg)
    args['--log-level'] = _LOG_LEVELS[args.get('--log-level', 'info')]
    args['--timeout'] = args.get('--timeout', 60)
    return args


def _parse_addr(addr):
    """Parse ``addr`` and returns a ``('host', port)`` tuple.

    If the host does not look like an IP(v4) address, resolve its name
    to an IP address.

    Raise a :exc:`ValueError` if resolving the hostname fails or if the
    address contains no host or port.

    """
    try:
        host, port = addr.strip().split(':')
        # Resolve hostname if it doesn't look like an IP address
        if not re.match(r'^(\d{1,3}\.){3}\d{1,3}$', host):
            host = socket.gethostbyname(host)
        addr = (host, int(port))
        return addr

    except (ValueError):
        raise ValueError('Error parsing "%s"' % addr)

    except (IOError, OSError):
        raise ValueError('Could not resolve "%s"' % addr[0])
