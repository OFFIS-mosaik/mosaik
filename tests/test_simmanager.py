import sys

from example_sim.mosaik import ExampleSim
from simpy.io.json import JSON as JsonRpc
from simpy.io.message import Message
from simpy.io.network import RemoteException
from simpy.io.packet import PacketUTF8 as Packet
import mosaik_api
import pytest

from mosaik import scenario
from mosaik import simmanager
from mosaik.exceptions import ScenarioError
import mosaik

from .util import SimMock


sim_config = {
    'ExampleSimA': {
        'python': 'example_sim.mosaik:ExampleSim',
    },
    'ExampleSimB': {
        'cmd': 'pyexamplesim %(addr)s',
        'cwd': '.',
    },
    'ExampleSimC': {
        'connect': 'localhost:5556',
    },
    'ExampleSimD': {
    },
    'Fail': {
        'cmd': 'python -c "import time; time.sleep(0.2)"',
    },
    'SimMock': {
        'python': 'tests.util:SimMock',
    },
}


@pytest.yield_fixture
def world():
    world = scenario.World(sim_config)
    yield world
    if world.srv_sock:
        world.shutdown()


def test_start(world, monkeypatch):
    """Test if start() dispatches to the correct start functions."""
    class proxy:
        meta = {
            'api_version': mosaik_api.__api_version__,
        }
    start = lambda *args, **kwargs: proxy
    monkeypatch.setattr(simmanager, 'start_inproc', start)
    monkeypatch.setattr(simmanager, 'start_proc', start)
    monkeypatch.setattr(simmanager, 'start_connect', start)

    ret = simmanager.start(world, 'ExampleSimA', '0', {})
    assert ret == proxy

    ret = simmanager.start(world, 'ExampleSimB', '0', {})
    assert ret == proxy

    ret = simmanager.start(world, 'ExampleSimC', '0', {})
    assert ret == proxy


def test_start_wrong_api_version(world, monkeypatch):
    """An exception should be raised if the simulator uses an unsupported
    API version."""
    monkeypatch.setattr(mosaik.simmanager, 'API_VERSION', 1)
    exc_info = pytest.raises(ScenarioError, simmanager.start, world,
                             'ExampleSimA', '0', {})
    assert str(exc_info.value) == (
        '"ExampleSimA" API version %s is not compatible with '
        'mosaik version %s.' % (mosaik_api.__api_version__,
                                mosaik.simmanager.API_VERSION))


def test_start_inproc(world):
    """Test starting an in-proc simulator."""
    sp = simmanager.start(world, 'ExampleSimA', 'ExampleSim-0',
                          {'step_size': 2})
    assert sp.sid == 'ExampleSim-0'
    assert sp.meta
    assert isinstance(sp._inst, ExampleSim)
    assert sp._inst.step_size == 2


def test_start_proc(world):
    """Test starting a simulator as external process."""
    sp = simmanager.start(world, 'ExampleSimB', 'ExampleSim-0', {})
    assert sp.sid == 'ExampleSim-0'
    assert 'api_version' in sp.meta and 'models' in sp.meta
    sp.stop()


def test_start_proc_timeout_accept(world, capsys):
    world.config['start_timeout'] = 0.1
    pytest.raises(SystemExit, simmanager.start, world, 'Fail', '', {})
    out, err = capsys.readouterr()
    assert out == ('ERROR: Simulator "Fail" did not connect to mosaik in '
                   'time.\nMosaik terminating\n')
    assert err == ''


def test_start_connect(world):
    """Test connecting to an already running simulator."""
    env = world.env
    sock = scenario.backend.TCPSocket.server(env, ('127.0.0.1', 5556))

    def sim():
        msock = yield sock.accept()
        channel = Message(env, Packet(msock))
        req = yield channel.recv()
        req.succeed(ExampleSim().meta)
        yield channel.recv()  # Wait for stop message
        channel.close()

    def starter():
        sp = simmanager.start(world, 'ExampleSimC', 'ExampleSim-0', {})
        assert sp.sid == 'ExampleSim-0'
        assert sp._proc is None
        assert 'api_version' in sp.meta and 'models' in sp.meta
        yield from sp.stop()
        yield env.event().succeed()

    sim_proc = env.process(sim())
    starter_proc = env.process(starter())
    env.run(until=sim_proc & starter_proc)
    sock.close()


def test_start_connect_timeout_init(world, capsys):
    """Test connecting to an already running simulator."""
    world.config['start_timeout'] = 0.1
    env = world.env
    sock = scenario.backend.TCPSocket.server(env, ('127.0.0.1', 5556))

    def sim():
        msock = yield sock.accept()
        channel = Message(env, Packet(msock))
        yield channel.recv()
        import time
        time.sleep(0.15)
        channel.close()

    def starter():
        pytest.raises(SystemExit, simmanager.start, world, 'ExampleSimC',
                      '', {})
        out, err = capsys.readouterr()
        assert out == ('ERROR: Simulator "ExampleSimC" did not reply to the '
                       'init() call in time.\nMosaik terminating\n')
        assert err == ''

        yield env.event().succeed()

    sim_proc = env.process(sim())
    starter_proc = env.process(starter())
    env.run(until=sim_proc & starter_proc)
    sock.close()


def test_start_connect_stop_timeout(world):
    """Test connecting to an already running simulator.

    When asked to stop, the simulator times out.

    """
    env = world.env
    sock = scenario.backend.TCPSocket.server(env, ('127.0.0.1', 5556))

    def sim():
        msock = yield sock.accept()
        channel = Message(env, Packet(msock))
        req = yield channel.recv()
        req.succeed(ExampleSim().meta)
        yield channel.recv()  # Wait for stop message

    def starter():
        sp = simmanager.start(world, 'ExampleSimC', 'ExampleSim-0', {})
        sp._stop_timeout = 0.01
        assert sp.sid == 'ExampleSim-0'
        assert sp._proc is None
        assert 'api_version' in sp.meta and 'models' in sp.meta
        yield from sp.stop()
        yield env.event().succeed()

    sim_proc = env.process(sim())
    starter_proc = env.process(starter())
    env.run(until=sim_proc & starter_proc)
    sock.close()


@pytest.mark.parametrize(('sim_config', 'err_msg'), [
    ({}, 'Not found in sim_config'),
    ({'spam': {}}, 'Invalid configuration'),
    ({'spam': {'python': 'eggs'}}, 'Malformed Python class name: Expected '
                                   '"module:Class"'),
    ({'spam': {'python': 'eggs:Bacon'}}, 'Could not import module: '
                                         "No module named 'eggs'"),
    ({'spam': {'python': 'example_sim:Bacon'}}, 'Class not found in module'),
    ({'spam': {'cmd': 'foo'}}, "No such file or directory: 'foo'"),
    ({'spam': {'cmd': 'python', 'cwd': 'bar'}}, "No such file or directory: "
                                                "'bar'"),
    ({'spam': {'connect': 'eggs'}}, 'Could not parse address "eggs"'),
])
def test_start_user_error(sim_config, err_msg):
    """Test failure at starting an in-proc simulator."""
    world = scenario.World(sim_config)
    with pytest.raises(ScenarioError) as exc_info:
        simmanager.start(world, 'spam', '', {})
    if sys.platform != 'win32':  # pragma: no cover
        # Windows has strange error messages which do not want to check :(
        assert str(exc_info.value) == ('Simulator "spam" could not be '
                                       'started: ' + err_msg)
    world.shutdown()


def test_start_sim_error(capsys):
    """Test connection failures of external processes."""
    world = scenario.World({'spam': {'connect': 'foo:1234'}})
    pytest.raises(SystemExit, simmanager.start, world, 'spam', '',
                  {'foo': 'bar'})

    out, err = capsys.readouterr()
    assert out == ('ERROR: Simulator "spam" could not be started: Could not '
                   'connect to "foo:1234"\nMosaik terminating\n')
    assert err == ''


def test_start_init_error(capsys):
    """Test simulator crashing during init()."""
    world = scenario.World({'spam': {'cmd': 'pyexamplesim %(addr)s'}})
    pytest.raises(SystemExit, simmanager.start, world, 'spam', '', {'foo': 3})

    out, err = capsys.readouterr()
    assert out.startswith('ERROR: ')
    assert out.endswith('Simulator "spam" closed its connection during the '
                        'init() call.\nMosaik terminating\n')
    assert err == ''


@pytest.mark.parametrize(['version', 'valid'], [
    (2, True),
    (2.0, True),
    ('2', False),
    (1, False),
    (2.1, False),
    (3, False),
])
def test_valid_api_version(version, valid):
    assert simmanager.valid_api_version(version, 2) == valid


def test_sim_proxy():
    """SimProxy should not be instantiateable."""
    pytest.raises(NotImplementedError, simmanager.SimProxy, 'spam', 'id',
                  {'models': {}}, None)


def test_sim_proxy_illegal_model_names(world):
    pytest.raises(ScenarioError, simmanager.LocalProcess, '', 0,
                  {'models': {'step': {}}}, SimMock(), world)


def test_sim_proxy_illegal_extra_methods(world):
    pytest.raises(ScenarioError, simmanager.LocalProcess, '', 0,
                  {'models': {'A': {}}, 'extra_methods': ['step']}, SimMock(),
                  world)
    pytest.raises(ScenarioError, simmanager.LocalProcess, '', 0,
                  {'models': {'A': {}}, 'extra_methods': ['A']}, SimMock(),
                  world)


def test_sim_proxy_stop_impl():
    class Test(simmanager.SimProxy):
        # Does not implement SimProxy.stop(). Should raise an error.
        def _get_proxy(self, name):
            return None

    t = Test('spam', 'id', {'models': {}}, None)
    pytest.raises(NotImplementedError, t.stop)


def test_local_process():
    class world:
        env = None

    es = ExampleSim()
    sp = simmanager.LocalProcess('ExampleSim', 'ExampleSim-0', es.meta, es,
                                 world)
    assert sp.name == 'ExampleSim'
    assert sp.sid == 'ExampleSim-0'
    assert sp._inst is es
    assert sp.meta is es.meta
    assert sp.last_step == float('-inf')
    assert sp.next_step == 0
    assert sp.step_required is None


def test_local_process_finalized(world):
    """Test that ``finalize()`` is called for local processes (issue #23)."""
    sm = world.start('SimMock')
    assert sm._sim._inst.finalized is False
    world.run(until=1)
    assert sm._sim._inst.finalized is True


def _rpc_get_progress(mosaik, world):
    """Helper for :func:`test_mosaik_remote()` that checks the "get_progress()"
    RPC."""
    prog = yield mosaik.get_progress()
    assert prog == 23


def _rpc_get_related_entities(mosaik, world):
    """Helper for :func:`test_mosaik_remote()` that checks the
    "get_related_entities()" RPC."""
    # No param yields complete entity graph
    entities = yield mosaik.get_related_entities()
    for edge in entities['edges']:
        edge[:2] = sorted(edge[:2])
    entities['edges'].sort()
    assert entities == {
        'nodes': {
            'X.0': {'sim': 'ExampleSim', 'type': 'A'},
            'X.1': {'sim': 'ExampleSim', 'type': 'A'},
            'X.2': {'sim': 'ExampleSim', 'type': 'A'},
            'X.3': {'sim': 'ExampleSim', 'type': 'A'},
        },
        'edges': [
            ['X.0', 'X.1', {}],
            ['X.0', 'X.2', {}],
            ['X.1', 'X.2', {}],
            ['X.2', 'X.3', {}],
        ],
    }

    # Single string yields dict with related entities
    entities = yield mosaik.get_related_entities('X.0')
    assert entities == {
        'X.1': {'sim': 'ExampleSim', 'type': 'A'},
        'X.2': {'sim': 'ExampleSim', 'type': 'A'},
    }

    # List of strings yields dicts with related entities grouped by input ids
    entities = yield mosaik.get_related_entities(['X.1', 'X.2'])
    assert entities == {
        'X.1': {
            'X.0': {'sim': 'ExampleSim', 'type': 'A'},
            'X.2': {'sim': 'ExampleSim', 'type': 'A'},
        },
        'X.2': {
            'X.0': {'sim': 'ExampleSim', 'type': 'A'},
            'X.1': {'sim': 'ExampleSim', 'type': 'A'},
            'X.3': {'sim': 'ExampleSim', 'type': 'A'},
        },
    }


def _rpc_get_data(mosaik, world):
    """Helper for :func:`test_mosaik_remote()` that checks the "get_data()"
    RPC."""
    data = yield mosaik.get_data({'X.2': ['attr']})
    assert data == {'X.2': {'attr': 'val'}}


def _rpc_set_data(mosaik, world):
    """Helper for :func:`test_mosaik_remote()` that checks the "set_data()"
    RPC."""
    yield mosaik.set_data({'src': {'X.2': {'val': 23}}})
    assert world.sims['X'].input_buffer == {
        '2': {'val': {'src': 23}},
    }

    yield mosaik.set_data({'src': {'X.2': {'val': 42}}})
    assert world.sims['X'].input_buffer == {
        '2': {'val': {'src': 42}},
    }


def _rpc_get_data_err1(mosaik, world):
    """Required simulator not connected to us."""
    yield mosaik.get_data({'Z.2': []})


def _rpc_get_data_err2(mosaik, world):
    """Async-requests flag not set for connection."""
    yield mosaik.get_data({'Y.2': []})


def _rpc_set_data_err1(mosaik, world):
    """Required simulator not connected to us."""
    yield mosaik.set_data({'src': {'Z.2': {'val': 42}}})


def _rpc_set_data_err2(mosaik, world):
    """Async-requests flag not set for connection."""
    yield mosaik.set_data({'src': {'Y.2': {'val': 42}}})


@pytest.mark.parametrize(('rpc', 'err'), [
    (_rpc_get_progress, None),
    (_rpc_get_related_entities, None),
    (_rpc_get_data, None),
    (_rpc_set_data, None),
    (_rpc_get_data_err1, ScenarioError),
    (_rpc_get_data_err2, ScenarioError),
    (_rpc_set_data_err1, RemoteException),
    (_rpc_set_data_err2, RemoteException),
])
def test_mosaik_remote(rpc, err):
    backend = simmanager.backend
    world = scenario.World({})
    env = world.env

    edges = [(0, 1), (0, 2), (1, 2), (2, 3)]
    edges = [('X.%s' % x, 'X.%s' % y) for x, y in edges]
    world.df_graph.add_edge('X', 'X', async_requests=True)
    world.df_graph.add_edge('Y', 'X', async_requests=False)
    world.df_graph.add_node('Z')
    world.entity_graph.add_edges_from(edges)
    for node in world.entity_graph:
        world.entity_graph.add_node(node, sim='ExampleSim', type='A')
    world.sim_progress = 23
    world._df_cache = {
        1: {
            'X': {'2': {'attr': 'val'}},
        },
    }

    def simulator():
        sock = backend.TCPSocket.connection(env, ('localhost', 5555))
        rpc_con = JsonRpc(Packet(sock))
        mosaik = rpc_con.remote

        try:
            yield from rpc(mosaik, world)
        finally:
            sock.close()

    def greeter():
        sock = yield world.srv_sock.accept()
        rpc_con = JsonRpc(Packet(sock))
        proxy = simmanager.RemoteProcess('X', 'X', {'models': {}}, None,
                                         rpc_con, world)
        proxy.last_step = proxy.next_step = 1
        world.sims['X'] = proxy

    env.process(greeter())
    if err is None:
        env.run(env.process(simulator()))
    else:
        pytest.raises(err, env.run, env.process(simulator()))
    world.srv_sock.close()
