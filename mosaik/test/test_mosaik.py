"""
Test a complete mosaik simulation using mosaik as a library.

"""
from mosaik import scenario


sim_config = {
    'PyExampleSim': {
        'python': 'example_sim.mosaik:ExampleSim',
    },
}


def test_mosaik():
    env = scenario.Environment(sim_config)
    create_scenario(env)
    env.run(until=10)
    for sim in env.sims.values():
        assert sim.time == 10
    assert 0


def create_scenario(env):
    exsim1 = env.start('PyExampleSim')
    exsim2 = env.start('PyExampleSim')

    assert isinstance(exsim1, scenario.ModelFactory)
    assert isinstance(exsim1.A, scenario.ModelMock)
    assert isinstance(exsim2, scenario.ModelFactory)
    assert isinstance(exsim2.B, scenario.ModelMock)

    a = [exsim1.A(init_val=0) for i in range(3)]
    b = exsim2.B.create(2, init_val=0)

    for i, entity in enumerate(sorted(a, key=lambda e: (e.sid, e.eid))):
        assert entity.sid == 'PyExampleSim-0'
        assert entity.eid == '%d.0' % i
        assert entity.type == 'A'
        assert entity.rel == []
        assert entity.sim == exsim1._sim

    for i, entity in enumerate(sorted(b, key=lambda e: (e.sid, e.eid))):
        assert entity.sid == 'PyExampleSim-1'
        assert entity.eid == '0.%d' % i
        assert entity.type == 'B'
        assert entity.rel == []
        assert entity.sim == exsim2._sim

    for i, j in zip(a, b):
        env.connect(i, j, ('val_out', 'val_in'))
    # env.connect((0, 1), a, b)
