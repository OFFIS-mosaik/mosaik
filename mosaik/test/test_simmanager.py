from unittest import mock
import sys

from example_sim.mosaik import ExampleSim
from simpy.io.json import JSON as JsonRpc
from simpy.io.message import Message
from simpy.io.packet import PacketUTF8 as Packet
import pytest

from mosaik import scenario
from mosaik import simmanager
from mosaik.exceptions import ScenarioError
import mosaik
import mosaik_api


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
}


@pytest.yield_fixture
def world():
    world = scenario.World(sim_config)
    yield world
    world.shutdown()


def test_start(world):
    """Test if start() dispatches to the correct start functions."""
    with mock.patch('mosaik.simmanager.start_inproc') as a, \
            mock.patch('mosaik.simmanager.start_proc') as b, \
            mock.patch('mosaik.simmanager.start_connect') as c:
        proxy = mock.Mock()
        proxy.meta = {
            'api_version': mosaik_api.__version__,
        }
        a.return_value = b.return_value = c.return_value = proxy

        ret = simmanager.start(world, 'ExampleSimA', '0', {})
        assert a.call_count == 1
        assert ret == a.return_value

        ret = simmanager.start(world, 'ExampleSimB', '0', {})
        assert b.call_count == 1
        assert ret == b.return_value

        ret = simmanager.start(world, 'ExampleSimC', '0', {})
        assert c.call_count == 1
        assert ret == c.return_value


def test_start_wrong_api_version(world):
    """An exception should be raised if the "major" part of the simulator's
    API version differs from mosaik's version's "major" part."""
    with mock.patch.object(mosaik, '__version__', '42.0.0'):
        exc_info = pytest.raises(ScenarioError, simmanager.start,
                                 world, 'ExampleSimA', '0', {})
        assert str(exc_info.value) == (
            '"ExampleSimA" API version %s is not compatible with '
            'mosaik version %s.' % (mosaik_api.__version__,
                                    mosaik.__version__))


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


def test_start_proc_timeout_accept(world):
    world.config['start_timeout'] = 0.1
    exc_info = pytest.raises(ScenarioError, simmanager.start, world, 'Fail',
                             '', {})
    assert str(exc_info.value) == ('Simulator "Fail" did not connect to '
                                   'mosaik in time.')


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


def test_start_connect_timeout_init(world):
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
        exc_info = pytest.raises(ScenarioError, simmanager.start, world,
                                 'ExampleSimC', '', {})
        assert str(exc_info.value) == ('Simulator "ExampleSimC" did not reply '
                                       'to the init() call in time.')
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
    ({'spam': {'python': 'eggs:Bacon'}}, 'Could not import module'),
    ({'spam': {'python': 'example_sim:Bacon'}}, 'Class not found in module'),
    ({'spam': {'cmd': 'foo'}}, "No such file or directory: 'foo'"),
    ({'spam': {'cmd': 'python', 'cwd': 'bar'}}, "No such file or directory: "
                                                "'bar'"),
    ({'spam': {'connect': 'eggs'}}, 'Could not parse address "eggs"'),
    ({'spam': {'connect': 'eggs:23'}}, 'Could not connect to "eggs:23"'),
])
def test_start__error(sim_config, err_msg):
    """Test failure at starting an in-proc simulator."""
    world = scenario.World(sim_config)
    with pytest.raises(ScenarioError) as exc_info:
        simmanager.start(world, 'spam', '', {})
    if not sys.platform == 'win32':  # pragma: no cover
        # Windows has strange error messages which do not want to check :(
        assert str(exc_info.value) == ('Simulator "spam" could not be '
                                       'started: ' + err_msg)
    world.shutdown()


@pytest.mark.parametrize(['version', 'valid'], [
    ('2.0', True),
    ('2.2.2', True),
    ('2.1.1', True),
    ('1.9', False),
    ('3.0', False),
])
def test_is_valid_api_version(version, valid):
    with mock.patch.object(mosaik, '__version__', '2.1.1'):
        assert simmanager.is_valid_api_version(version) == valid


def test_sim_proxy():
    """SimProxy should not be instantiateable."""
    pytest.raises(NotImplementedError, simmanager.SimProxy, 'spam', {})


def test_sim_proxy_stop_impl():
    class Test(simmanager.SimProxy):
        # Does not implement SimProxy.stop(). Should raise an error.
        def _proxy_call(self, name):
            return None

    t = Test('spam', {})
    pytest.raises(NotImplementedError, t.stop)


def test_local_process():
    es = ExampleSim()
    sp = simmanager.LocalProcess(None, 'ExampleSim-0', es, None, es.meta)
    assert sp.sid == 'ExampleSim-0'
    assert sp._inst is es
    assert sp.meta is es.meta
    assert sp.last_step == float('-inf')
    assert sp.next_step == 0
    assert sp.step_required is None


def _rpc_get_progress(mosaik, world):
    """Helper for :func:`test_mosaik_remote()` that checks the "get_progress()"
    RPC."""
    prog = yield mosaik.get_progress()
    assert prog == 23


def _rpc_get_related_entities(mosaik, world):
    """Helper for :func:`test_mosaik_remote()` that checks the
    "get_related_entities()" RPC."""
    entities = yield mosaik.get_related_entities('0')
    assert entities == {'0': [['X/1', 'A'], ['X/2', 'A']]}

    entities = yield mosaik.get_related_entities(['1', 'X/2'])
    assert entities == {'1': [['X/0', 'A'], ['X/2', 'A']],
                        'X/2': [['X/0', 'A'], ['X/1', 'A'], ['X/3', 'A']]}


def _rpc_get_data(mosaik, world):
    """Helper for :func:`test_mosaik_remote()` that checks the "get_data()"
    RPC."""
    data = yield mosaik.get_data({'X/2': ['attr']})
    assert data == {'X/2': {'attr': 'val'}}


def _rpc_set_data(mosaik, world):
    """Helper for :func:`test_mosaik_remote()` that checks the "set_data()"
    RPC."""
    yield mosaik.set_data({'X/2': {'val': 23}})
    assert world.sims['X'].input_buffer == {
        '2': {'val': [23]},
    }

    yield mosaik.set_data({'X/2': {'val': 42}})
    assert world.sims['X'].input_buffer == {
        '2': {'val': [42]},
    }


@pytest.mark.parametrize('rpc', [
    _rpc_get_progress,
    _rpc_get_related_entities,
    _rpc_get_data,
    _rpc_set_data,
])
def test_mosaik_remote(rpc):
    backend = simmanager.backend
    world = scenario.World({})
    env = world.env

    edges = [(0, 1), (0, 2), (1, 2), (2, 3)]
    edges = [('X/%s' % x, 'X/%s' % y) for x, y in edges]
    world.entity_graph.add_edges_from(edges)
    for node in world.entity_graph:
        world.entity_graph.add_node(node, entity=scenario.Entity('', '', 'A',
                                                                 [], None))
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
        proxy = simmanager.RemoteProcess(world, 'X', None, rpc_con, {})
        proxy.last_step = proxy.next_step = 1
        world.sims['X'] = proxy

    env.process(greeter())
    env.run(env.process(simulator()))
    world.srv_sock.close()
