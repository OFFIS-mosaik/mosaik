import sys

from example_sim.mosaik import ExampleSim
from simpy.io.json import JSON as JSON_RPC  # JSON is actually an object
from simpy.io.message import Message
from simpy.io.network import RemoteException
from simpy.io.packet import PacketUTF8 as Packet
from mosaik_api import __api_version__ as api_version
import pytest

from mosaik import scenario
from mosaik import simmanager
from mosaik.exceptions import ScenarioError
import mosaik

from tests.mocks.simulator_mock import SimulatorMock

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
    'SimulatorMock': {
        'python': 'tests.mocks.simulator_mock:SimulatorMock',
    },
}


@pytest.fixture(name='world')
def world_fixture():
    world = scenario.World(sim_config)
    yield world
    if world.srv_sock:
        world.shutdown()


def test_start(world, monkeypatch):
    """
    Test if start() dispatches to the correct start functions.
    """

    class Proxy(object):
        meta = {
            'api_version': api_version,
            'models': {}
        }

    start = lambda *args, **kwargs: Proxy  # flake8: noqa

    s = simmanager.StarterCollection()
    monkeypatch.setitem(s, 'python', start)
    monkeypatch.setitem(s, 'cmd', start)
    monkeypatch.setitem(s, 'connect', start)

    ret = simmanager.start(world, 'ExampleSimA', '0', 1., {})
    assert ret == Proxy

    # The api_version has to be re-initialized, because it is changed in
    # simmanager.start()
    Proxy.meta['api_version'] = api_version
    ret = simmanager.start(world, 'ExampleSimB', '0', 1., {})
    assert ret == Proxy

    # The api_version has to re-initialized
    Proxy.meta['api_version'] = api_version
    ret = simmanager.start(world, 'ExampleSimC', '0', 1., {})
    assert ret == Proxy


def test_start_wrong_api_version(world, monkeypatch):
    """
    An exception should be raised if the simulator uses an unsupported
    API version."""
    monkeypatch.setattr(mosaik.simmanager, 'API_MAJOR', 1000)
    monkeypatch.setattr(mosaik.simmanager, 'API_MINOR', 5)
    exc_info = pytest.raises(ScenarioError, simmanager.start, world,
                             'ExampleSimA', '0', 1., {})

    assert str(exc_info.value) in ('Simulator "ExampleSimA" could not be '
                                   'started: Invalid version "%(API_VERSION)s":'
                                   ' Version must be between 1000.0 and 1000.5'
                                   % {'API_VERSION': api_version})


def test_start_in_process(world):
    """
    Test starting an in-proc simulator."""
    sp = simmanager.start(world, 'ExampleSimA', 'ExampleSim-0', 1.,
                          {'step_size': 2})
    assert sp.sid == 'ExampleSim-0'
    assert sp.meta
    assert isinstance(sp._inst, ExampleSim)
    assert sp._inst.step_size == 2


def test_start_external_process(world):
    """
    Test starting a simulator as external process."""
    sp = simmanager.start(world, 'ExampleSimB', 'ExampleSim-0', 1., {})
    assert sp.sid == 'ExampleSim-0'
    assert 'api_version' in sp.meta and 'models' in sp.meta
    sp.stop()


def test_start_proc_timeout_accept(world, capsys):
    world.config['start_timeout'] = 0.1
    pytest.raises(SystemExit, simmanager.start, world, 'Fail', '', 1., {})
    out, err = capsys.readouterr()
    assert out == ('ERROR: Simulator "Fail" did not connect to mosaik in '
                   'time.\nMosaik terminating\n')
    assert err == ''


def test_start_external_process_with_environment_variables(world, tmpdir):
    """
    Assert that you can set environment variables for a new sub-process.
    """
    # Replace sim_config for this test:
    print(tmpdir.strpath)
    world.sim_config = {'SimulatorMockTmp': {
        'cmd': '%(python)s -m simulator_mock %(addr)s',
        'env': {
            'PYTHONPATH': tmpdir.strpath,
        },
    }}

    # Write the module "simulator_mock.py" to tmpdir:
    tmpdir.join('simulator_mock.py').write("""
import mosaik_api


class SimulatorMock(mosaik_api.Simulator):
    def __init__(self):
        super().__init__(meta={})


if __name__ == '__main__':
    mosaik_api.start_simulation(SimulatorMock())
""")
    sim = world.start('SimulatorMockTmp')


def test_start_connect(world):
    """
    Test connecting to an already running simulator.
    """
    env = world.env
    sock = scenario.backend.TCPSocket.server(env, ('127.0.0.1', 5556))

    def sim():
        socket = yield sock.accept()
        channel = Message(env, Packet(socket))
        req = yield channel.recv()
        req.succeed(ExampleSim().meta)
        yield channel.recv()  # Wait for stop message
        channel.close()

    def starter():
        sp = simmanager.start(world, 'ExampleSimC', 'ExampleSim-0', 1., {})
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
    """
    Test connecting to an already running simulator.
    """
    world.config['start_timeout'] = 0.1
    env = world.env
    sock = scenario.backend.TCPSocket.server(env, ('127.0.0.1', 5556))

    def sim():
        socket = yield sock.accept()
        channel = Message(env, Packet(socket))
        yield channel.recv()
        import time
        time.sleep(0.15)
        channel.close()

    def starter():
        pytest.raises(SystemExit, simmanager.start, world, 'ExampleSimC',
                      '', 1., {})
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
    """
    Test connecting to an already running simulator.

    When asked to stop, the simulator times out.
    """
    env = world.env
    sock = scenario.backend.TCPSocket.server(env, ('127.0.0.1', 5556))

    def sim():
        socket = yield sock.accept()
        channel = Message(env, Packet(socket))
        req = yield channel.recv()
        req.succeed(ExampleSim().meta)
        yield channel.recv()  # Wait for stop message

    def starter():
        sp = simmanager.start(world, 'ExampleSimC', 'ExampleSim-0', 1., {})
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
    ({'spam': {'python': 'eggs'}}, 'Malformed Python class name: Expected "module:Class" --> not enough values to '
                                   'unpack (expected 2, got 1)'),
    ({'spam': {'python': 'eggs:Bacon'}}, 'Could not import module: '
                                         "No module named 'eggs' --> No module named 'eggs'"),
    ({'spam': {'python': 'example_sim:Bacon'}}, "Class not found in module --> module 'example_sim' has no attribute "
                                                "'Bacon'"),
    ({'spam': {'cmd': 'foo'}}, "No such file or directory: 'foo'"),
    ({'spam': {'cmd': 'python', 'cwd': 'bar'}}, "No such file or directory: "
                                                "'bar'"),
    ({'spam': {'connect': 'eggs'}}, 'Could not parse address "eggs"'),
])
def test_start_user_error(sim_config, err_msg):
    """
    Test failure at starting an in-proc simulator.
    """
    world = scenario.World(sim_config)
    try:
        with pytest.raises(ScenarioError) as exc_info:
            simmanager.start(world, 'spam', '', 1., {})
        if sys.platform != 'win32':  # pragma: no cover
            # Windows has strange error messages which do not want to check :(
            assert str(exc_info.value) == ('Simulator "spam" could not be '
                                           'started: ' + err_msg)
    finally:
        world.shutdown()


def test_start_sim_error(capsys):
    """
    Test connection failures of external processes.
    """
    world = scenario.World({'spam': {'connect': 'foo:1234'}})
    try:
        pytest.raises(SystemExit, simmanager.start, world, 'spam', '', 1.,
                      {'foo': 'bar'})

        out, err = capsys.readouterr()
        assert out == ('ERROR: Simulator "spam" could not be started: Could '
                       'not connect to "foo:1234"\nMosaik terminating\n')
        assert err == ''
    finally:
        world.shutdown()


def test_start_init_error(capsys):
    """
    Test simulator crashing during init().
    """
    world = scenario.World({'spam': {'cmd': 'pyexamplesim %(addr)s'}})
    try:
        pytest.raises(SystemExit, simmanager.start, world,
                      'spam', '', 1., {'foo': 3})

        out, err = capsys.readouterr()
        assert out.startswith('ERROR: ')
        assert out.endswith('Simulator "spam" closed its connection during '
                            'the init() call.\nMosaik terminating\n')
        assert err == ''
    finally:
        world.shutdown()


@pytest.mark.parametrize(['version', 'result'], [
    ('3.0', (3, 0)),
    (3.0, (3, 0)),
])
def test_validate_api_version(version, result):
    assert simmanager.validate_api_version(version) == result


@pytest.mark.parametrize('version', [
    '1',
    '1.2',
    '2',
    '2,1',
    2,
    2.11,
    '3.99',
    '4.1',
    '3a',
])
def test_validate_api_version_wrong_version(version):
    with pytest.raises(ScenarioError) as se:
        simmanager.validate_api_version(version)
        assert 'Invalid version' in str(se.value)


def test_sim_proxy():
    """
    SimProxy should not be instantiateable.
    """
    pytest.raises(NotImplementedError, simmanager.SimProxy, 'spam', 'id',
                  {'models': {}}, None)


def test_sim_proxy_illegal_model_names(world):
    pytest.raises(ScenarioError, simmanager.LocalProcess, '', 0,
                  {'models': {'step': {}}}, SimulatorMock('time-based'), world)


def test_sim_proxy_illegal_extra_methods(world):
    pytest.raises(ScenarioError, simmanager.LocalProcess, '', 0,
                  {'models': {'A': {}}, 'extra_methods': ['step']},
                  SimulatorMock('time-based'), world)
    pytest.raises(ScenarioError, simmanager.LocalProcess, '', 0,
                  {'models': {'A': {}}, 'extra_methods': ['A']},
                  SimulatorMock('time-based'), world)


def test_sim_proxy_stop_impl():
    class Test(simmanager.SimProxy):
        def stop(self):
            raise NotImplementedError()

        # Does not implement SimProxy.stop(). Should raise an error.
        def _get_proxy(self, name):
            return None

    t = Test('spam', 'id', {'models': {}}, None)
    pytest.raises(NotImplementedError, t.stop)


def test_local_process():
    class World:
        env = None

    es = ExampleSim()
    sp = simmanager.LocalProcess('ExampleSim', 'ExampleSim-0', es.meta, es,
                                 World)
    assert sp.name == 'ExampleSim'
    assert sp.sid == 'ExampleSim-0'
    assert sp._inst is es
    assert sp.meta is es.meta
    assert sp.last_step == -1
    assert sp.next_step is None
    assert sp.next_steps == [0]


def test_local_process_finalized(world):
    """
    Test that ``finalize()`` is called for local processes (issue #23).
    """
    simulator = world.start('SimulatorMock')
    assert simulator._sim._inst.finalized is False
    world.run(until=1)
    assert simulator._sim._inst.finalized is True


def _rpc_get_progress(mosaik, world):
    """
    Helper for :func:`test_mosaik_remote()` that checks the "get_progress()"
    RPC.
    """
    progress = yield mosaik.get_progress()
    assert progress == 23


def _rpc_get_related_entities(mosaik, world):
    """
    Helper for :func:`test_mosaik_remote()` that checks the
    "get_related_entities()" RPC.
    """
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
    """
    Helper for :func:`test_mosaik_remote()` that checks the "get_data()"
    RPC.
    """
    data = yield mosaik.get_data({'X.2': ['attr']})
    assert data == {'X.2': {'attr': 'val'}}


def _rpc_set_data(mosaik, world):
    """
    Helper for :func:`test_mosaik_remote()` that checks the "set_data()"
    RPC.
    """
    yield mosaik.set_data({'src': {'X.2': {'val': 23}}})
    assert world.sims['X'].input_buffer == {
        '2': {'val': {'src': 23}},
    }

    yield mosaik.set_data({'src': {'X.2': {'val': 42}}})
    assert world.sims['X'].input_buffer == {
        '2': {'val': {'src': 42}},
    }


def _rpc_get_data_err1(mosaik, world):
    """
    Required simulator not connected to us.
    """
    try:
        yield mosaik.get_data({'Z.2': []})
    except RemoteException as exception:
        if _remote_exception_type(exception) == \
                'mosaik.exceptions.ScenarioError':
            raise ScenarioError


def _remote_exception_type(exception):
    remote_exception_type = \
        exception.remote_traceback.split('\n')[-2].split(':')[0]
    return remote_exception_type


def _rpc_get_data_err2(mosaik, world):
    """
    Async-requests flag not set for connection.
    """
    try:
        yield mosaik.get_data({'Y.2': []})
    except RemoteException as exception:
        if _remote_exception_type(exception) == \
                'mosaik.exceptions.ScenarioError':
            raise ScenarioError


def _rpc_set_data_err1(mosaik, world):
    """
    Required simulator not connected to us.
    """
    yield mosaik.set_data({'src': {'Z.2': {'val': 42}}})


def _rpc_set_data_err2(mosaik, world):
    """
    Async-requests flag not set for connection.
    """
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

    try:
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
            rpc_con = JSON_RPC(Packet(sock))
            mosaik_remote = rpc_con.remote

            try:
                yield from rpc(mosaik_remote, world)
            finally:
                sock.close()

        def greeter():
            sock = yield world.srv_sock.accept()
            rpc_con = JSON_RPC(Packet(sock))
            proxy = simmanager.RemoteProcess('X', 'X', {'models': {}}, None,
                                             rpc_con, world)
            proxy.last_step = proxy.next_step = 1
            world.sims['X'] = proxy

        env.process(greeter())
        if err is None:
            env.run(env.process(simulator()))
        else:
            pytest.raises(err, env.run, env.process(simulator()))

    finally:
        world.srv_sock.close()


def test_timed_input_buffer():
    """Test TimedInputBuffer, especially if a lower value is added at the same
    time for the same connection.
    """
    buffer = simmanager.TimedInputBuffer()
    buffer.add(1, 'src_sid', 'src_eid', 'dest_eid', 'dest_var', 2)
    buffer.add(1, 'src_sid', 'src_eid', 'dest_eid', 'dest_var', 1)
    buffer.add(2, 'src_sid', 'src_eid', 'dest_eid', 'dest_var', 0)
    input_dict = buffer.get_input({}, 0)
    assert input_dict == {}
    input_dict = buffer.get_input({}, 1)
    assert input_dict == {'dest_eid': {'dest_var': {'src_sid.src_eid': 1}}}

def test_global_time_resolution(world):
    # Default time resolution set to 1.0
    simulator = world.start('SimulatorMock')
    assert simulator._sim._world.time_resolution == 1.0

    # Set global time resolution to 60.0
    world.time_resolution = 60.0
    simulator_2 = world.start('SimulatorMock')
    assert simulator_2._sim._world.time_resolution == 60.0