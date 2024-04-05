from typing import List, cast

from networkx import to_dict_of_dicts as to_dict

from mosaik import scenario
from mosaik.scenario import Entity, ModelFactory, World
from mosaik.exceptions import ScenarioError
import pytest

from mosaik.tiered_time import TieredInterval

sim_config: scenario.SimConfig = {
    'ExampleSim': {
        'python': 'example_sim.mosaik:ExampleSim',
    },
    'MetaMirror': {
        'python': 'tests.simulators.meta_mirror:MetaMirror',
    },
    'MetaMirror2.0': {
        'python': 'tests.simulators.meta_mirror:MetaMirror',
        'api_version': '2.0',
    },
    'GenericTestSimulator': {
        'python': 'tests.simulators.generic_test_simulator:TestSim',
    }
}


@pytest.fixture(name='world')
def world_fixture():
    world = World(sim_config)
    yield world
    world.shutdown()


@pytest.fixture
def mf(world: World):
    return world.start('ExampleSim')


def test_entity():
    class ModelMockMock:
        name = 'spam'
        def __repr__(self):
            return "ModelMockMock"
    sim = object()
    e = scenario.Entity('0', '1', 'sim', ModelMockMock(), [])
    assert e.sid == '0'
    assert e.eid == '1'
    assert e.sim_name == 'sim'
    assert e.type == 'spam'
    assert str(e) == "Entity(model='spam', eid='1', sid='0')"
    assert repr(e) == "Entity(model_mock=ModelMockMock, eid='1', sid='0', children=[])"


def test_world():
    sim_config = {'spam': 'eggs'}
    mosaik_config = {'start_timeout': 23}
    world = World(sim_config, mosaik_config)
    try:
        assert world.sim_config is sim_config
        assert world.time_resolution == 1.0
        assert world.config['start_timeout'] == 23
        assert world.sims == {}
        assert world.loop
        assert not hasattr(world, 'execution_graph')
    finally:
        world.shutdown()


def test_two_worlds():
    """Test that two worlds can exist without a port conflict."""
    world_1 = World({})
    world_2 = World({})
    world_1.shutdown()
    world_2.shutdown()


def test_world_debug():
    world = World(sim_config, debug=True)
    try:
        assert world.execution_graph.adj == {}
    finally:
        world.shutdown()


def test_world_start(world: World):
    """
    Test starting new simulators and getting IDs for them.
    """
    fac = world.start('ExampleSim', step_size=2)
    assert isinstance(fac, ModelFactory)
    assert len(world.sims) == 1
    assert world.sims['ExampleSim-0']._proxy == fac._proxy
    assert fac._proxy.sim.step_size == 2
    assert world.time_resolution == 1.0
    assert 'ExampleSim-0' in world.sims

    world.start('ExampleSim')
    assert list(sorted(world.sims)) == ['ExampleSim-0', 'ExampleSim-1']
    assert 'ExampleSim-1' in world.sims

def test_global_time_resolution():
    """
    Test if the simulator process has the correct time_resolution
    """
    world = scenario.World(sim_config, time_resolution=60.0)

    try:
        fac = world.start('ExampleSim', step_size=2)
        # TODO: Test whether the resolution "reaches" the simulator
        assert world.time_resolution == 60.0
    finally:
        world.shutdown()

def test_world_connect(world: World):
    """
    Test connecting to single entities.
    """
    sim_0 = world.start("ExampleSim")
    sim_1 = world.start("ExampleSim")
    a = cast(List[Entity], sim_0.A.create(2, init_val=0))
    b = cast(List[Entity], sim_1.B.create(2, init_val=0))
    for i, j in zip(a, b):
        world.connect(i, j, ('val_out', 'val_in'), ('dummy_out', 'dummy_in'))

    sim_0 = world.sims[sim_0._sid]
    sim_1 = world.sims[sim_1._sid]
    
    # TODO: check for connections in new place
    assert sim_0.successors == {sim_1: TieredInterval(0)}
    assert sim_0.successors_to_wait_for == {}
    assert sim_1.successors == {}
    assert sim_1.input_delays[sim_0] == TieredInterval(0)

    assert sim_1.pulled_inputs[(sim_0, TieredInterval(0))] == set([
        ((a[0].eid, 'val_out'), (b[0].eid, 'val_in')),
        ((a[0].eid, 'dummy_out'), (b[0].eid, 'dummy_in')),
        ((a[1].eid, 'val_out'), (b[1].eid, 'val_in')),
        ((a[1].eid, 'dummy_out'), (b[1].eid, 'dummy_in')),
    ])
    
    assert to_dict(world.entity_graph) == {
        'ExampleSim-0.' + a[0].eid: {'ExampleSim-1.' + b[0].eid: {}},
        'ExampleSim-1.' + b[0].eid: {'ExampleSim-0.' + a[0].eid: {}},
        'ExampleSim-0.' + a[1].eid: {'ExampleSim-1.' + b[1].eid: {}},
        'ExampleSim-1.' + b[1].eid: {'ExampleSim-0.' + a[1].eid: {}},
    }


def test_world_connect_same_simulator(world: World):
    """Connections to entities belonging to the same simulator must have
    a delay (time-shifted or weak).
    """
    a = world.start('ExampleSim').A.create(2, init_val=0)
    with pytest.raises(ScenarioError) as err:
        world.connect(a[0], a[1], ('val_out', 'val_out'))
        world.run(1)
    assert "Your scenario contains cycles" in str(err.value)


def test_world_connect_cycle(world: World):
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
    assert (
        "Your scenario contains cycles" in str(err.value)
    )


def test_group_cycle(world: World):
    with world.group():
        a = world.start('ExampleSim').B(init_val=0)
        b = world.start('ExampleSim').B(init_val=0)
    c = world.start('ExampleSim').B(init_val=0)
    world.connect_one(a, b, 'val_out', 'val_in', weak=True, initial_data=None)
    world.connect_one(b, c, 'val_out', 'val_in')
    world.connect_one(c, a, 'val_out', 'val_in')
    with pytest.raises(ScenarioError) as err:
        world.run(0)
    assert "Your scenario contains cycles" in str(err.value)


def test_world_connect_wrong_attr_names(world: World):
    """
    The entities to be connected must have the listed attributes.
    """
    a = world.start('ExampleSim', sim_id="A").A(init_val=0)
    b = world.start('ExampleSim', sim_id="B").B(init_val=0)
    with pytest.raises(ScenarioError) as err:
        world.connect(a, b, ('val', 'val_in'))
    assert "connecting A.0.0.val to B.0.0.val_in" in str(err.value)
    assert "source attribute" in str(err.value)

    with pytest.raises(ScenarioError) as err:
        world.connect(a, b, ('val_out', 'val'))
    assert "connecting A.0.0.val_out to B.0.0.val" in str(err.value)
    assert "destination attribute"

    with pytest.raises(ScenarioError) as err:
        world.connect(a, b, ('val', 'val_in'), 'onoes')
    assert "connecting A.0.0.val to B.0.0.val_in" in str(err.value)
    assert "connecting A.0.0.onoes to B.0.0.onoes" in str(err.value)
    assert "source attribute" in str(err.value)
    assert "destination attribute" in str(err.value)


def test_world_connect_no_attrs(world: World):
    """
    Connecting two entities without passing a list of attrs should work.
    """
    a = world.start('ExampleSim').A(init_val=0)
    b = world.start('ExampleSim').B(init_val=0)
    world.connect(a, b)

    sim_0 = world.sims["ExampleSim-0"]
    sim_1 = world.sims["ExampleSim-1"]

    sim_0.successors = set((sim_1,))
    sim_1.successors = set()
    sim_1.input_delays = {sim_0: TieredInterval(0)}
    assert world.entity_graph.adj == {
        'ExampleSim-0.' + a.eid: {'ExampleSim-1.' + b.eid: {}},
        'ExampleSim-1.' + b.eid: {'ExampleSim-0.' + a.eid: {}},
    }


def test_world_connect_any_inputs(world: World):
    """
    Check if a model sets ``'any_inputs': True`` in its meta data,
    everything can be connected to it.
    """
    a = cast(Entity, world.start('ExampleSim').A(init_val=0))
    b = cast(Entity, world.start(
        'MetaMirror',
        meta={
            "api_version": "3.0",
            "type": "time-based",
            "models": {"B": {"any_inputs": True, "attrs": []}},
        }
    ).B())
    sim_a = world.sims[a.sid]
    sim_b = world.sims[b.sid]
    world.connect(a, b, 'val_out')

    assert sim_b.pulled_inputs[(sim_a, TieredInterval(0))] == set([
        ((a.eid, "val_out"), (b.eid, "val_out")),
    ])
    
    assert sim_a.successors == {sim_b: TieredInterval(0)}
    assert sim_b.input_delays[sim_a] == TieredInterval(0)
    assert to_dict(world.entity_graph) == {
        'ExampleSim-0.' + a.eid: {'MetaMirror-0.' + b.eid: {}},
        'MetaMirror-0.' + b.eid: {'ExampleSim-0.' + a.eid: {}},
    }


@pytest.mark.filterwarnings("ignore:Connections with async_requests")
def test_world_connect_async_requests(world: World):
    a = world.start('ExampleSim').A(init_val=0)
    b = world.start('ExampleSim').B(init_val=0)
    world.connect(a, b, async_requests=True)
    sim_a = world.sims[a.sid]
    sim_b = world.sims[b.sid]
    sim_a.successors_to_wait_for = set((sim_b,))


def test_world_connect_time_shifted(world: World):
    a = cast(Entity, world.start('ExampleSim').A(init_val=0))
    b = cast(Entity, world.start('ExampleSim').B(init_val=0))
    sim_a = world.sims[a.sid]
    sim_b = world.sims[b.sid]
    world.connect(a, b, 'val_out', time_shifted=True, initial_data={'val_out': 1.0})

    assert sim_b.pulled_inputs[(sim_a, TieredInterval(1))] == set([
        ((a.eid, 'val_out'), (b.eid, 'val_out')),
    ])
    assert sim_a.successors == {sim_b: TieredInterval(0)}
    assert sim_b.input_delays[sim_a] == TieredInterval(1)
    assert world.sims['ExampleSim-0'].outputs[-1] == {
        a.eid: {
            'val_out': 1.0
        },
    }


def test_weak_outside_group(world: World):
    a = world.start('ExampleSim').A(init_val=0)
    b = world.start('ExampleSim').B(init_val=0)
    with pytest.raises(ScenarioError) as exc:
        world.connect(a, b, "val_out", weak=True, initial_data={"val_out": 0})
    assert "in groups" in str(exc.value)


def test_world_get_data(world: World):
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


def test_world_run_twice(world: World):
    world.start('ExampleSim')
    world.run(0)
    with pytest.raises(RuntimeError):
        world.run(1)


def test_model_factory(world: World, mf: ModelFactory):
    assert 'A' in dir(mf)
    assert 'B' in dir(mf)
    assert mf.A.name == 'A'
    assert mf.B.name == 'B'


def test_model_factory_check_params(world: World, mf: ModelFactory):
    einfo = pytest.raises(TypeError, mf.A, spam='eggs')
    assert str(einfo.value) == "create() got unexpected keyword arguments: 'spam'"

def async_mock(return_value):
    async def f(*args, **kwargs):
        return return_value
    return f


def test_model_factory_hierarchical_entities(world: World, mf: ModelFactory):
    ret = [{
        'eid': 'a', 'type': 'A', 'rel': [], 'children': [{
            'eid': 'b', 'type': 'B', 'rel': [], 'children': [{
                'eid': 'c', 'type': 'C', 'rel': [],
            }],
        }]
    }]
    mf.A._proxy.send = async_mock(return_value=ret)

    a = mf.A(init_val=1)
    assert len(a.children) == 1

    b = a.children[0]
    assert type(b) is scenario.Entity
    assert len(b.children) == 1

    c = b.children[0]
    assert type(c) is scenario.Entity
    assert len(c.children) == 0


def test_model_factory_wrong_entity_count(world: World, mf: ModelFactory):
    ret = [None, None, None]
    mf.A._proxy.send = async_mock(return_value=ret)
    with pytest.raises(AssertionError) as err:
        mf.A.create(2, init_val=0)
    assert str(err.value) == '2 entities were requested but 3 were created.'


def test_model_factory_wrong_model(world: World, mf: ModelFactory):
    ret = [{'eid': 'spam_0', 'type': 'Spam'}]
    mf.A._proxy.send = async_mock(return_value=ret)
    with pytest.raises(AssertionError) as err:
        mf.A.create(1, init_val=0)
    assert str(err.value) == ('Entity "spam_0" has the wrong type: "Spam"; '
                              '"A" required.')


def test_model_factory_hierarchical_entities_illegal_type(world: World, mf: ModelFactory):
    ret = [{
        'eid': 'a', 'type': 'A', 'rel': [], 'children': [{
            'eid': 'b', 'type': 'B', 'rel': [], 'children': [{
                'eid': 'c', 'type': 'Spam', 'rel': [],
            }],
        }]
    }]
    mf.A._proxy.send = async_mock(return_value=ret)

    with pytest.raises(AssertionError) as err:
        mf.A.create(1, init_val=0)
    assert str(err.value) == ('Type "Spam" of entity "c" not found in sim\'s '
                              'meta data.')


def test_model_factory_private_model(world: World, mf: ModelFactory):
    with pytest.raises(AttributeError) as err:
        getattr(mf, 'C')
    assert str(err.value) == 'Model "C" is not public.'


def test_model_factory_unkown_model(world: World, mf: ModelFactory):
    with pytest.raises(AttributeError) as err:
        getattr(mf, 'D')
    assert (
        str(err.value)
        == 'Model factory for "ExampleSim-0" has no model and no function "D".'
    )


def test_model_mock_entity_graph(world: World):
    """
    Test if related entities are added to the entity_graph.
    """

    async def send(*args, **kwargs):
        entities = [
            {'eid': '0', 'type': 'A', 'rel': ['1']},
            {'eid': '1', 'type': 'A', 'rel': []},
        ]
        return entities

    fac = world.start('ExampleSim')
    fac._proxy.send = send
    
    assert world.entity_graph.adj == {}
    fac.A.create(2)
    assert world.entity_graph.adj == {
        'ExampleSim-0.0': {'ExampleSim-0.1': {}},
        'ExampleSim-0.1': {'ExampleSim-0.0': {}},
    }
    assert world.entity_graph.nodes['ExampleSim-0.0']['sid'] == 'ExampleSim-0'
    assert world.entity_graph.nodes['ExampleSim-0.1']['sid'] == 'ExampleSim-0'
    assert world.entity_graph.nodes['ExampleSim-0.0']['type'] == 'A'
    assert world.entity_graph.nodes['ExampleSim-0.1']['type'] == 'A'


def test_extra_methods(world: World):
    sim = world.start(
        'MetaMirror', 
        meta={
            "api_version": "3.0",
            "type": "time-based",
            "models": {},
            "extra_methods": ["foo", "bar"],
        },
    )
    assert hasattr(sim, "foo")
    assert hasattr(sim, "bar")


def test_no_extra_methods(world: World):
    # This should not throw an exception, despite not having
    # "extra_methods" in the meta, as it is optional.
    world.start(
        'MetaMirror',
        meta={
            "api_version": "3.0",
            "type": "time-based",
            "models": {},
        },
    )


def test_extra_info(world: World):
    sim = world.start("GenericTestSimulator")
    entity = sim.A(extra_info=42)
    assert entity.extra_info == 42


def test_missing_type_in_meta(world: World):
    with pytest.raises(ScenarioError) as exc:
        world.start(
            "MetaMirror",
            meta={
                "api_version": "3.0",
                "models": {},
            }
        )
    assert "missing a type specification" in str(exc)


def test_typo_in_type_in_meta(world: World):
    with pytest.raises(ScenarioError) as exc:
        world.start(
            "MetaMirror",
            meta={
                "api_version": "3.0",
                "type": "timebased",
                "models": {},
            }
        )
    assert "not a valid type" in str(exc)


def test_missing_type_in_old_api(world: World):
    sim = world.start(
        "MetaMirror2.0",
        meta={
            "api_version": "2.0",
            "models": {},
        }
    )
    assert sim.type == "time-based"
