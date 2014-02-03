from unittest import mock

from example_sim.mosaik import ExampleSim
import pytest

from mosaik import simmanager
from mosaik.exceptions import ScenarioError


sim_config = {
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


def test_start_inproc():
    """Test starting an in-proc simulator."""
    sp = simmanager.start('ExampleSimA', sim_config, 'ExampleSim-0')
    assert sp.sid == 'ExampleSim-0'
    assert isinstance(sp.inst, ExampleSim)


@pytest.mark.parametrize(('sim_config', 'err_msg'), [
    ({}, 'Not found in sim_config'),
    ({'spam': {'python': 'eggs'}}, 'Malformed Python class name: Expected '
                                   '"module:Class"'),
    ({'spam': {'python': 'eggs:Bacon'}}, 'Could not import module'),
    ({'spam': {'python': 'example_sim:Bacon'}}, 'Class not found in module'),
])
def test_start_inproc_error(sim_config, err_msg):
    """Test failure at starting an in-proc simulator."""
    with pytest.raises(ScenarioError) as exc_info:
        simmanager.start('spam', sim_config, '')
    assert str(exc_info.value) == ('Simulator "spam" could not be started: ' +
                                   err_msg)


@pytest.mark.xfail
def test_start_proc():
    """Test starting a simulator as external process."""
    assert 0


@pytest.mark.xfail
def test_start_proc_error():
    """Test failure at starting a simulator as external process."""
    assert 0


@pytest.mark.xfail
def test_start_connect():
    """Test connecting to an already running simulator."""
    assert 0


@pytest.mark.xfail
def test_start_connect_error():
    """Test failure at connecting to an already running simulator."""
    assert 0


def test_sim_proxy():
    es = ExampleSim()
    sp = simmanager.SimProxy('ExampleSim-0', es)
    assert sp.sid == 'ExampleSim-0'
    assert sp.inst is es
    assert sp.meta is es.meta
    assert sp.time == 0


def test_sim_proxy_meth_forward():
    sp = simmanager.SimProxy('', mock.Mock())
    meths = [
        ('create', (object(), object(), object())),
        ('step', (object(), object(), object())),
    ]
    for meth, args in meths:
        ret = getattr(sp, meth)(*args)
        assert ret is getattr(sp.inst, meth).return_value
        assert getattr(sp.inst, meth).call_args == mock.call(*args)
