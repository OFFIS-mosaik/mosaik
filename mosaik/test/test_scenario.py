from unittest import mock

from simpy.io.network import RemoteException
import pytest

from mosaik import scenario, simmanager, simulator
from mosaik.exceptions import ScenarioError
from mosaik.test.util import SimMock


sim_config = {
    'ExampleSim': {
        'python': 'example_sim.mosaik:ExampleSim',
    },
}


@pytest.yield_fixture
def world():
    world = scenario.World(sim_config)
    yield world
    world.shutdown()


def test_entity():
    sim = object()
    e = scenario.Entity('0', '1', 'spam', [], sim)
    assert e.sid == '0'
    assert e.eid == '1'
    assert e.type == 'spam'
    assert e.rel == []
    assert e.sim is sim
    assert str(e) == 'Entity(0, 1, spam)'
    assert repr(e) == 'Entity(0, 1, spam, [], %r)' % sim


def test_world():
    sim_config = {'spam': 'eggs'}
    world = scenario.World(sim_config)
    assert world.sim_config is sim_config
    assert world.sims == {}
    assert world.env
    assert world.df_graph.nodes() == []
    assert world.df_graph.edges() == []
    assert not hasattr(world, 'execution_graph')
    world.shutdown()


def test_world_debug():
    world = scenario.World(sim_config, execution_graph=True)
    assert world.execution_graph.adj == {}
    world.shutdown()


def test_world_start(world):
    """Test starting new simulators and getting IDs for them."""
    fac = world.start('ExampleSim', step_size=2)
    assert isinstance(fac, scenario.ModelFactory)
    assert world.sims == {'ExampleSim-0': fac._sim}
    assert fac._sim._inst.step_size == 2
    assert 'ExampleSim-0' in world.df_graph

    world.start('ExampleSim')
    assert list(sorted(world.sims)) == ['ExampleSim-0', 'ExampleSim-1']
    assert 'ExampleSim-1' in world.df_graph


def test_world_connect(world):
    """Test connecting to single entities."""
    a = world.start('ExampleSim').A.create(2, init_val=0)
    b = world.start('ExampleSim').B.create(2, init_val=0)
    for i, j in zip(a, b):
        world.connect(i, j, ('val_out', 'val_in'), ('dummy_out', 'dummy_in'))

    assert world.df_graph.adj == {
        'ExampleSim-0': {
            'ExampleSim-1': {
                'async_requests': False,
                'dataflows': [
                    (a[0].eid, b[0].eid, (('val_out', 'val_in'),
                                          ('dummy_out', 'dummy_in'))),
                    (a[1].eid, b[1].eid, (('val_out', 'val_in'),
                                          ('dummy_out', 'dummy_in'))),
                ],
            },
        },
        'ExampleSim-1': {},
    }
    assert world.entity_graph.adj == {
        'ExampleSim-0/' + a[0].eid: {'ExampleSim-1/' + b[0].eid: {}},
        'ExampleSim-1/' + b[0].eid: {'ExampleSim-0/' + a[0].eid: {}},
        'ExampleSim-0/' + a[1].eid: {'ExampleSim-1/' + b[1].eid: {}},
        'ExampleSim-1/' + b[1].eid: {'ExampleSim-0/' + a[1].eid: {}},
    }
    assert world._df_outattr == {
        'ExampleSim-0': {
            '0.0': ['val_out', 'dummy_out'],
            '0.1': ['val_out', 'dummy_out']
        },
    }


def test_world_connect_same_simulator(world):
    """Connecting to entities belonging to the same simulator must fail."""
    a = world.start('ExampleSim').A.create(2, init_val=0)
    with pytest.raises(ScenarioError) as err:
        world.connect(a[0], a[1], ('val_out', 'val_out'))
    assert str(err.value) == ('Cannot connect entities sharing the same '
                              'simulator.')
    assert world.df_graph.edges() == []
    assert world._df_outattr == {}


def test_world_connect_cycle(world):
    """If connecting two entities results in a cycle in the dataflow graph,
    an error must be raised."""
    a = world.start('ExampleSim').A(init_val=0)
    b = world.start('ExampleSim').B(init_val=0)
    world.connect(a[0], b[0], ('val_out', 'val_in'))
    with pytest.raises(ScenarioError) as err:
        world.connect(b[0], a[0], ('val_in', 'val_out'))
    assert str(err.value) == ('Connection from "ExampleSim-1" to '
                              '"ExampleSim-0" introduces cyclic dependencies.')
    assert world.df_graph.edges() == [('ExampleSim-0', 'ExampleSim-1')]
    assert len(world._df_outattr) == 1


def test_world_connect_wrong_attr_names(world):
    """The entities to be connected must have the listed attributes."""
    a = world.start('ExampleSim').A(init_val=0)[0]
    b = world.start('ExampleSim').B(init_val=0)[0]
    err = pytest.raises(ScenarioError, world.connect, a, b, ('val', 'val_in'))
    assert str(err.value) == ('At least on attribute does not exist: '
                              'Entity(ExampleSim-0, 0.0, A).val')
    err = pytest.raises(ScenarioError, world.connect, a, b, ('val_out', 'val'))
    assert str(err.value) == ('At least on attribute does not exist: '
                              'Entity(ExampleSim-1, 0.0, B).val')
    err = pytest.raises(ScenarioError, world.connect, a, b, ('val', 'val_in'),
                        ('dummy_out', 'onoes'))
    assert str(err.value) == ('At least on attribute does not exist: '
                              'Entity(ExampleSim-0, 0.0, A).val, '
                              'Entity(ExampleSim-1, 0.0, B).onoes')
    assert world.df_graph.edges() == []
    assert world._df_outattr == {}


def test_world_connect_no_attrs(world):
    """Connecting two entities without passing a list of attrs should work."""
    a = world.start('ExampleSim').A(init_val=0)
    b = world.start('ExampleSim').B(init_val=0)
    world.connect(a[0], b[0])

    assert world.df_graph.adj == {
        'ExampleSim-0': {
            'ExampleSim-1': {
                'async_requests': False,
                'dataflows': [(a[0].eid, b[0].eid, ())],
            },
        },
        'ExampleSim-1': {},
    }
    assert world.entity_graph.adj == {
        'ExampleSim-0/' + a[0].eid: {'ExampleSim-1/' + b[0].eid: {}},
        'ExampleSim-1/' + b[0].eid: {'ExampleSim-0/' + a[0].eid: {}},
    }
    assert world._df_outattr == {}


def test_world_connect_async_requests(world):
    a = world.start('ExampleSim').A(init_val=0)
    b = world.start('ExampleSim').B(init_val=0)
    world.connect(a[0], b[0], async_requests=True)

    assert world.df_graph.adj == {
        'ExampleSim-0': {
            'ExampleSim-1': {
                'async_requests': True,
                'dataflows': [(a[0].eid, b[0].eid, ())],
            },
        },
        'ExampleSim-1': {},
    }


def test_world_run():
    world = scenario.World({})
    world.sims = {0: simmanager.LocalProcess(world, 0, SimMock(), world.env,
                                             {})}
    with mock.patch('mosaik.simulator.run') as run_mock:
        world.run(3)
        assert run_mock.call_args == mock.call(world, 3)

    world.shutdown()


def test_world_run_with_debug():
    world = scenario.World({}, execution_graph=True)

    def run(*args, **kwargs):
        assert simulator.step.__name__ == 'wrapped_step'

    assert simulator.run.__name__ == 'run'
    with mock.patch('mosaik.simulator.run', run):
        world.run(3)
    assert simulator.run.__name__ == 'run'

    world.shutdown()


def test_model_factory(world):
    mf = world.start('ExampleSim')
    assert mf.A._name == 'A'
    assert mf.A._sim_id == mf._sim.sid
    assert mf.B._name == 'B'


def test_model_factory_private_model(world):
    mf = world.start('ExampleSim')
    err = pytest.raises(ScenarioError, getattr, mf, 'C')
    assert str(err.value) == 'Model "C" is not public.'


def test_model_factory_unkown_model(world):
    mf = world.start('ExampleSim')
    err = pytest.raises(ScenarioError, getattr, mf, 'D')
    assert str(err.value) == ('Model factory for "ExampleSim-0" has no model '
                              '"D".')


def test_model_mock_entity_graph(world):
    """Test if related entites are added to the entity_graph."""
    def create(*args, **kwargs):
        entities = [
            {'eid': '0', 'type': 'A', 'rel': ['1']},
            {'eid': '1', 'type': 'A', 'rel': []},
        ]
        return world.env.event().succeed(entities)

    sp_mock = mock.Mock()
    sp_mock.create = create
    sp_mock.sid = 'E0'

    fac = world.start('ExampleSim')
    fac._sim = sp_mock

    assert world.entity_graph.adj == {}
    fac.A.create(2)
    assert world.entity_graph.adj == {
        'E0/0': {'E0/1': {}},
        'E0/1': {'E0/0': {}},
    }
    assert world.entity_graph.node['E0/0']['entity'].type == 'A'
    assert world.entity_graph.node['E0/1']['entity'].type == 'A'


@pytest.mark.parametrize(['error', 'errmsg'], [
    (ConnectionResetError(),
     'ERROR: "ExampleSim" closed its connection during its initialization '
     'phase.\nMosaik terminating\n'),
    (RemoteException('spam', 'eggs'),
     'RemoteException:\neggs\n————————————————\nMosaik terminating\n'),

])
def test_start_errors(world, error, errmsg, capsys):
    """Test sims breaking during their start."""
    with mock.patch('mosaik.simmanager.start') as start:
        start.side_effect = error
        pytest.raises(SystemExit, world.start, 'ExampleSim')
    errmsg = 'Starting "ExampleSim" as "ExampleSim-0" ...\n' + errmsg
    out, err = capsys.readouterr()
    assert out == errmsg
    assert err == ''


@pytest.mark.parametrize(['error', 'errmsg'], [
    (ConnectionResetError(),
     'ERROR: "Mock" closed its connection during the creation of 1 instances '
     'of "spam".\nMosaik terminating\n'),
    (RemoteException('spam', 'eggs'),
     'RemoteException:\neggs\n————————————————\nMosaik terminating\n'),

])
def test_create_errors(world, error, errmsg, capsys):
    """Test sims breaking while creating entities."""
    sim = mock.Mock()
    sim.sid = 'Mock'
    sim.create.side_effect = error

    mm = scenario.ModelMock(world, 'spam', sim)
    pytest.raises(SystemExit, mm.create, 1)

    out, err = capsys.readouterr()
    assert out == errmsg
    assert err == ''


@pytest.mark.parametrize(['error', 'errmsg'], [
    (ConnectionResetError(),
     'ERROR: A simulator closed its connection.\nMosaik terminating\n'),
    (RemoteException('spam', 'eggs'),
     'RemoteException:\neggs\n————————————————\nMosaik terminating\n'),
    (KeyboardInterrupt(), 'Simulation canceled. Terminating ...\n')

])
def test_run_errors(world, error, errmsg, capsys):
    """Test sims breaking during the simulation."""
    with mock.patch('mosaik.simulator.run') as run:
        run.side_effect = error
        pytest.raises(SystemExit, world.run, 1)

    errmsg = 'Starting simulation.\n' + errmsg
    out, err = capsys.readouterr()
    assert out == errmsg
    assert err == ''
