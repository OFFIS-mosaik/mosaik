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
    start = '2014-01-01 00:00:00'
    stop =  '2014-01-02 00:00:00'
    env = scenario.Environment(start, stop, sim_config)
    create_scenario(env)
    scenario.run(env)


def create_scenario(env):
    exsim = env.start('PyExampleSim')

    assert isinstance(exsim, scenario.ModelFactory)
    assert isinstance(exsim.A, scenario.ModelMock)
    assert isinstance(exsim.B, scenario.ModelMock)

    a = [exsim.A(init_val=0) for i in range(3)]
    b = exsim.B.create(2, init_val=0)

    assert sorted(a, key=lambda x: x['eid']) == [
        {'eid': 'PyExampleSim-0.0.0', 'rel': [], 'etype': 'A'},
        {'eid': 'PyExampleSim-0.1.0', 'rel': [], 'etype': 'A'},
        {'eid': 'PyExampleSim-0.2.0', 'rel': [], 'etype': 'A'},
    ]
    assert sorted(b, key=lambda x: x['eid']) == [
        {'eid': 'PyExampleSim-0.3.0', 'rel': [], 'etype': 'B'},
        {'eid': 'PyExampleSim-0.3.1', 'rel': [], 'etype': 'B'},
    ]

    # env.connect((0, 1), a, b)
    # env.connect(a[0], b[0])
    # enc.connect(a[1], b[1])
