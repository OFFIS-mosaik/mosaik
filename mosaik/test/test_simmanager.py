from unittest import mock
import sys

from example_sim.mosaik import ExampleSim
from simpy.io.message import Message
from simpy.io.packet import PacketUTF8 as Packet
import pytest
import simpy.core

from mosaik import scenario
from mosaik import simmanager
from mosaik.exceptions import ScenarioError


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
        'slots': 1,
    },
    'ExampleSimD': {
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
        ret = simmanager.start(world, 'ExampleSimA', '0', {})
        assert a.call_count == 1
        assert ret == a.return_value

        ret = simmanager.start(world, 'ExampleSimB', '0', {})
        assert b.call_count == 1
        assert ret == b.return_value

        ret = simmanager.start(world, 'ExampleSimC', '0', {})
        assert c.call_count == 1
        assert ret == c.return_value


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


def test_start_connect(world):
    """Test connecting to an already running simulator."""
    env = world.env
    sock = scenario.backend.TCPSocket.server(env, ('127.0.0.1', 5556))

    def sim():
        msock = yield sock.accept()
        channel = Message(env, Packet(msock))
        req = yield channel.recv()
        req.succeed(ExampleSim().meta)
        try:
            yield channel.recv()  # Wait for stop message
        except:
            pass

    def starter():
        sp = simmanager.start(world, 'ExampleSimC', 'ExampleSim-0', {})
        assert sp.sid == 'ExampleSim-0'
        assert sp._proc is None
        assert 'api_version' in sp.meta and 'models' in sp.meta
        sp.stop()
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


def test_sim_proxy():
    """SimProxy should not be instantiateable."""
    pytest.raises(NotImplementedError, simmanager.SimProxy, 'spam', {})


def test_local_process():
    es = ExampleSim()
    sp = simmanager.LocalProcess('ExampleSim-0', es, None, es.meta)
    assert sp.sid == 'ExampleSim-0'
    assert sp._inst is es
    assert sp.meta is es.meta
    assert sp.last_step == float('-inf')
    assert sp.next_step == 0
    assert sp.step_required is None


def test_local_process_meth_forward():
    env = simpy.core.Environment()
    sp = simmanager.LocalProcess('', mock.Mock(), env, None)
    meths = [
        ('create', (object(), object(), object())),
        ('step', (object(), {})),
        ('get_data', (object(),)),
    ]
    for meth, args in meths:
        ret = getattr(sp, meth)(*args)
        assert ret.value is getattr(sp._inst, meth).return_value
        assert getattr(sp._inst, meth).call_args == mock.call(*args)
