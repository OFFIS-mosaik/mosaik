from unittest import mock
from networkx import to_dict_of_dicts as to_dict

from mosaik import scenario
from mosaik.exceptions import ScenarioError
import pytest

sim_config = {
    'ExampleSim': {
        'python': 'example_sim.mosaik:ExampleSim',
    },
}


@pytest.fixture(name='world')
def world_fixture():
    world = scenario.World(sim_config)
    yield world
    world.shutdown()


@pytest.fixture
def mf(world):
    return world.start('ExampleSim')


def test_entity():
    sim = object()
    e = scenario.Entity('0', '1', 'sim', 'spam', [], sim)
    assert e.sid == '0'
    assert e.eid == '1'
    assert e.sim_name == 'sim'
    assert e.type == 'spam'
    assert e.sim is sim
    assert str(e) == "Entity('0', '1', 'sim', spam)"
    assert repr(e) == "Entity('0', '1', 'sim', spam, [], %r)" % sim


def test_world():
    sim_config = {'spam': 'eggs'}
    mosaik_config = {'start_timeout': 23}
    world = scenario.World(sim_config, mosaik_config)
    try:
        assert world.sim_config is sim_config
        assert world.time_resolution == 1.0
        assert world.config['start_timeout'] == 23
        assert world.sims == {}
        assert world.loop
        assert list(world.df_graph.nodes()) == []
        assert list(world.df_graph.edges()) == []
        assert not hasattr(world, 'execution_graph')
    finally:
        world.shutdown()


def test_world_debug():
    world = scenario.World(sim_config, debug=True)
    try:
        assert world.execution_graph.adj == {}
    finally:
        world.shutdown()


def test_world_start(world):
    """
    Test starting new simulators and getting IDs for them.
    """
    fac = world.start('ExampleSim', step_size=2)
    assert isinstance(fac, scenario.ModelFactory)
    assert world.sims == {'ExampleSim-0': fac._sim}
    assert fac._sim.proxy.sim.step_size == 2
    assert fac._sim._world.time_resolution == 1.0
    assert 'ExampleSim-0' in world.df_graph

    world.start('ExampleSim')
    assert list(sorted(world.sims)) == ['ExampleSim-0', 'ExampleSim-1']
    assert 'ExampleSim-1' in world.df_graph

def test_global_time_resolution():
    """
    Test if the simulator process has the correct time_resolution
    """
    world = scenario.World(sim_config, time_resolution=60.0)

    try:
        fac = world.start('ExampleSim', step_size=2)
        assert fac._sim._world.time_resolution == 60.0
    finally:
        world.shutdown()

def test_world_connect(world):
    """
    Test connecting to single entities.
    """
    a = world.start('ExampleSim').A.create(2, init_val=0)
    b = world.start('ExampleSim').B.create(2, init_val=0)
    for i, j in zip(a, b):
        world.connect(i, j, ('val_out', 'val_in'), ('dummy_out', 'dummy_in'))

    connections = [
        (str(a[0].eid), str(b[0].eid), (('val_out', 'val_in'), ('dummy_out', 'dummy_in'))),
        (str(a[1].eid), str(b[1].eid), (('val_out', 'val_in'), ('dummy_out', 'dummy_in'))),
     ]

    assert to_dict(world.df_graph) == {
        'ExampleSim-0': {
            'ExampleSim-1': {
                'async_requests': False,
                'pred_waiting': False,
                'time_shifted': False,
                'weak': False,
                'trigger': set(),
                'dataflows': connections,
                'cached_connections': connections,
                'wait_async': world.df_graph['ExampleSim-0']['ExampleSim-1']['wait_async'],
                'wait_event': world.df_graph['ExampleSim-0']['ExampleSim-1']['wait_event'],
                'wait_lazy': world.df_graph['ExampleSim-0']['ExampleSim-1']['wait_lazy'],
            },
        },
        'ExampleSim-1': {},
    }
    assert to_dict(world.entity_graph) == {
        'ExampleSim-0.' + a[0].eid: {'ExampleSim-1.' + b[0].eid: {}},
        'ExampleSim-1.' + b[0].eid: {'ExampleSim-0.' + a[0].eid: {}},
        'ExampleSim-0.' + a[1].eid: {'ExampleSim-1.' + b[1].eid: {}},
        'ExampleSim-1.' + b[1].eid: {'ExampleSim-0.' + a[1].eid: {}},
    }
    assert world._df_outattr == {
        'ExampleSim-0': {
            '0.0': ['val_out', 'dummy_out'],
            '0.1': ['val_out', 'dummy_out']
        },
    }


def test_world_connect_same_simulator(world):
    """
    Connecting to entities belonging to the same simulator must fail.
    """
    a = world.start('ExampleSim').A.create(2, init_val=0)
    with pytest.raises(ScenarioError) as err:
        world.connect(a[0], a[1], ('val_out', 'val_out'))
    assert str(err.value) == ('Cannot connect entities sharing the same '
                              'simulator.')
    assert list(world.df_graph.edges()) == []
    assert dict(world._df_outattr) == {}


def test_world_connect_cycle(world):
    """
    If connecting two entities results in a cycle in the dataflow graph,
    an error must be raised.
    """
    a = world.start('ExampleSim').A(init_val=0)
    b = world.start('ExampleSim').B(init_val=0)
    world.connect(a, b, ('val_out', 'val_in'))
    world.connect(b, a, ('val_in', 'val_out'))
    with pytest.raises(ScenarioError) as err:
        world.run(1)
    assert str(err.value) == ('Scenario has unresolved cyclic dependencies: '
                              '[\'ExampleSim-0\', \'ExampleSim-1\']. Use '
                              'options "time-shifted" or "weak" for '
                              'resolution.')


def test_world_connect_wrong_attr_names(world):
    """
    The entities to be connected must have the listed attributes.
    """
    a = world.start('ExampleSim').A(init_val=0)
    b = world.start('ExampleSim').B(init_val=0)
    err = pytest.raises(ScenarioError, world.connect, a, b,
                        ('val', 'val_in'))
    assert str(err.value) == (
        'At least one attribute does not exist: '
        "Entity('ExampleSim-0', '0.0', 'ExampleSim', A).val")
    err = pytest.raises(ScenarioError, world.connect, a, b,
                        ('val_out', 'val'))
    assert str(err.value) == (
        'At least one attribute does not exist: '
        "Entity('ExampleSim-1', '0.0', 'ExampleSim', B).val")
    err = pytest.raises(ScenarioError, world.connect, a, b, ('val', 'val_in'),
                        'onoes')
    assert str(err.value) == (
        'At least one attribute does not exist: '
        "Entity('ExampleSim-0', '0.0', 'ExampleSim', A).val, "
        "Entity('ExampleSim-0', '0.0', 'ExampleSim', A).onoes, "
        "Entity('ExampleSim-1', '0.0', 'ExampleSim', B).onoes")
    assert list(world.df_graph.edges()) == []
    assert world._df_outattr == {}


def test_world_connect_no_attrs(world):
    """
    Connecting two entities without passing a list of attrs should work.
    """
    a = world.start('ExampleSim').A(init_val=0)
    b = world.start('ExampleSim').B(init_val=0)
    world.connect(a, b)

    assert to_dict(world.df_graph) == {
        'ExampleSim-0': {
            'ExampleSim-1': {
                'async_requests': False,
                'pred_waiting': False,
                'time_shifted': False,
                'weak': False,
                'trigger': set(),
                'dataflows': [(a.eid, b.eid, ())],
                'cached_connections': [],
                'wait_async': world.df_graph['ExampleSim-0']['ExampleSim-1']['wait_async'],
                'wait_event': world.df_graph['ExampleSim-0']['ExampleSim-1']['wait_event'],
                'wait_lazy': world.df_graph['ExampleSim-0']['ExampleSim-1']['wait_lazy'],
            },
        },
        'ExampleSim-1': {},
    }
    assert world.entity_graph.adj == {
        'ExampleSim-0.' + a.eid: {'ExampleSim-1.' + b.eid: {}},
        'ExampleSim-1.' + b.eid: {'ExampleSim-0.' + a.eid: {}},
    }
    assert world._df_outattr == {}


def test_world_connect_any_inputs(world):
    """
    Check if a model sets ``'any_inputs': True`` in its meta data,
    everything can be connected to it.
    """
    a = world.start('ExampleSim').A(init_val=0)
    b = world.start('ExampleSim').B(init_val=0)
    b.sim.proxy.meta['models']['B']['any_inputs'] = True
    world.connect(a, b, 'val_out')

    connections = [(a.eid, b.eid, (('val_out', 'val_out'),))]
    assert to_dict(world.df_graph) == {
        'ExampleSim-0': {
            'ExampleSim-1': {
                'async_requests': False,
                'pred_waiting': False,
                'time_shifted': False,
                'weak': False,
                'trigger': set(),
                'dataflows': connections,
                'cached_connections': connections,
                'wait_async': world.df_graph['ExampleSim-0']['ExampleSim-1']['wait_async'],
                'wait_event': world.df_graph['ExampleSim-0']['ExampleSim-1']['wait_event'],
                'wait_lazy': world.df_graph['ExampleSim-0']['ExampleSim-1']['wait_lazy'],
            },
        },
        'ExampleSim-1': {},
    }
    assert to_dict(world.entity_graph) == {
        'ExampleSim-0.' + a.eid: {'ExampleSim-1.' + b.eid: {}},
        'ExampleSim-1.' + b.eid: {'ExampleSim-0.' + a.eid: {}},
    }
    assert world._df_outattr == {
        'ExampleSim-0': {'0.0': ['val_out']},
    }


def test_world_connect_async_requests(world):
    a = world.start('ExampleSim').A(init_val=0)
    b = world.start('ExampleSim').B(init_val=0)
    world.connect(a, b, async_requests=True)

    assert to_dict(world.df_graph) == {
        'ExampleSim-0': {
            'ExampleSim-1': {
                'async_requests': True,
                'pred_waiting': True,
                'time_shifted': False,
                'weak': False,
                'trigger': set(),
                'dataflows': [(a.eid, b.eid, ())],
                'cached_connections': [],
                'wait_async': world.df_graph['ExampleSim-0']['ExampleSim-1']['wait_async'],
                'wait_event': world.df_graph['ExampleSim-0']['ExampleSim-1']['wait_event'],
                'wait_lazy': world.df_graph['ExampleSim-0']['ExampleSim-1']['wait_lazy'],
            },
        },
        'ExampleSim-1': {},
    }


def test_world_connect_time_shifted(world):
    a = world.start('ExampleSim').A(init_val=0)
    b = world.start('ExampleSim').B(init_val=0)
    world.connect(a, b, 'val_out', time_shifted=True, initial_data={'val_out': 1.0})

    connections = [(a.eid, b.eid, (('val_out', 'val_out'),))]
    assert to_dict(world.df_graph) == {
        'ExampleSim-0': {
            'ExampleSim-1': {
                'async_requests': False,
                'pred_waiting': False,
                'time_shifted': True,
                'weak': False,
                'trigger': set(),
                'dataflows': connections,
                'cached_connections': connections,
                'wait_async': world.df_graph['ExampleSim-0']['ExampleSim-1']['wait_async'],
                'wait_event': world.df_graph['ExampleSim-0']['ExampleSim-1']['wait_event'],
                'wait_lazy': world.df_graph['ExampleSim-0']['ExampleSim-1']['wait_lazy'],
            },
        },
        'ExampleSim-1': {},
    }

    assert world._df_cache == {
        -1: {
            'ExampleSim-0': {
                a.eid: {
                    'val_out': 1.0
                },
            },
        },
    }


@pytest.mark.parametrize('ctype', ['time_shifted', 'async_requests'])
def test_world_connect_different_types(world, ctype):
    a = world.start('ExampleSim').A(init_val=0)
    b = world.start('ExampleSim').B(init_val=0)
    world.connect(a, b)
    err = pytest.raises(ScenarioError, world.connect, a, b, **{ctype: True})
    assert str(err.value) == (f'{ctype.capitalize()} and standard connections '
                              'are mutually exclusive, but you have set both '
                              'between simulators ExampleSim-0 and '
                              'ExampleSim-1')


def test_world_get_data(world):
    sim1 = world.start('ExampleSim')
    sim2 = world.start('ExampleSim')

    es1 = sim1.A.create(2, init_val=1)
    es2 = sim2.B.create(1, init_val=2)

    data = world.get_data(es1 + es2, 'val_out')
    assert data == {
        es1[0]: {'val_out': 1},
        es1[1]: {'val_out': 1},
        es2[0]: {'val_out': 2},
    }


def test_world_run_twice(world):
    world.start('ExampleSim')
    world.run(0)
    with pytest.raises(RuntimeError):
        world.run(1)


def test_model_factory(world, mf):
    assert 'A' in dir(mf)
    assert 'B' in dir(mf)
    assert mf.A._name == 'A'
    assert mf.A._sim_id == mf._sim.sid
    assert mf.B._name == 'B'


def test_model_factory_check_params(world, mf):
    einfo = pytest.raises(TypeError, mf.A, spam='eggs')
    assert str(einfo.value) == "create() got an unexpected keyword argument " \
                               "'spam'"


def async_mock(return_value):
    async def f(*args, **kwargs):
        return return_value
    return f


def test_model_factory_hierarchical_entities(world, mf):
    ret = [{
        'eid': 'a', 'type': 'A', 'rel': [], 'children': [{
            'eid': 'b', 'type': 'B', 'rel': [], 'children': [{
                'eid': 'c', 'type': 'C', 'rel': [],
            }],
        }]
    }]
    mf.A._sim.proxy.create = async_mock(return_value=ret)

    a = mf.A(init_val=1)
    assert len(a.children) == 1

    b = a.children[0]
    assert type(b) is scenario.Entity
    assert len(b.children) == 1

    c = b.children[0]
    assert type(c) is scenario.Entity
    assert len(c.children) == 0


def test_model_factory_wrong_entity_count(world, mf):
    ret = [None, None, None]
    mf.A._sim.proxy.create = async_mock(return_value=ret)
    with pytest.raises(AssertionError) as err:
        mf.A.create(2, init_val=0)
    assert str(err.value) == '2 entities were requested but 3 were created.'


def test_model_factory_wrong_model(world, mf):
    ret = [{'eid': 'spam_0', 'type': 'Spam'}]
    mf.A._sim.proxy.create = async_mock(return_value=ret)
    with pytest.raises(AssertionError) as err:
        mf.A.create(1, init_val=0)
    assert str(err.value) == ('Entity "spam_0" has the wrong type: "Spam"; '
                              '"A" required.')


def test_model_factory_hierarchical_entities_illegal_type(world, mf):
    ret = [{
        'eid': 'a', 'type': 'A', 'rel': [], 'children': [{
            'eid': 'b', 'type': 'B', 'rel': [], 'children': [{
                'eid': 'c', 'type': 'Spam', 'rel': [],
            }],
        }]
    }]
    mf.A._sim.proxy.create = async_mock(return_value=ret)

    with pytest.raises(AssertionError) as err:
        mf.A.create(1, init_val=0)
    assert str(err.value) == ('Type "Spam" of entity "c" not found in sim\'s '
                              'meta data.')


def test_model_factory_private_model(world, mf):
    with pytest.raises(AttributeError) as err:
        getattr(mf, 'C')
    assert str(err.value) == 'Model "C" is not public.'


def test_model_factory_unkown_model(world, mf):
    with pytest.raises(AttributeError) as err:
        getattr(mf, 'D')
    assert str(err.value) == ('Model factory for "ExampleSim-0" has no model '
                              'and no function "D".')


def test_model_mock_entity_graph(world):
    """
    Test if related entities are added to the entity_graph.
    """

    async def create(*args, **kwargs):
        entities = [
            {'eid': '0', 'type': 'A', 'rel': ['1']},
            {'eid': '1', 'type': 'A', 'rel': []},
        ]
        return entities

    fac = world.start('ExampleSim')
    sp = fac._sim
    sp.proxy.create = create

    assert world.entity_graph.adj == {}
    fac.A.create(2)
    assert world.entity_graph.adj == {
        'ExampleSim-0.0': {'ExampleSim-0.1': {}},
        'ExampleSim-0.1': {'ExampleSim-0.0': {}},
    }
    assert world.entity_graph.nodes['ExampleSim-0.0']['sim'] == 'ExampleSim'
    assert world.entity_graph.nodes['ExampleSim-0.1']['sim'] == 'ExampleSim'
    assert world.entity_graph.nodes['ExampleSim-0.0']['type'] == 'A'
    assert world.entity_graph.nodes['ExampleSim-0.1']['type'] == 'A'
