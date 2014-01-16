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
    end = scenario.run(env, until=10)
    assert end == 10


def create_scenario(env):
    exsim1 = env.start('PyExampleSim')
    exsim2 = env.start('PyExampleSim')

    assert isinstance(exsim1, scenario.ModelFactory)
    assert isinstance(exsim1.A, scenario.ModelMock)
    assert isinstance(exsim2, scenario.ModelFactory)
    assert isinstance(exsim2.B, scenario.ModelMock)

    a = [exsim1.A(init_val=0) for i in range(3)]
    b = exsim2.B.create(2, init_val=0)

    assert sorted(a, key=lambda x: x['eid']) == [
        {'eid': 'PyExampleSim-0.0.0', 'rel': [], 'etype': 'A'},
        {'eid': 'PyExampleSim-0.1.0', 'rel': [], 'etype': 'A'},
        {'eid': 'PyExampleSim-0.2.0', 'rel': [], 'etype': 'A'},
    ]
    assert sorted(b, key=lambda x: x['eid']) == [
        {'eid': 'PyExampleSim-1.0.0', 'rel': [], 'etype': 'B'},
        {'eid': 'PyExampleSim-1.0.1', 'rel': [], 'etype': 'B'},
    ]

    # for i, j in zip(a, b):
    #     env.connect(i, j, ('val_out', 'val_in'))
    # env.connect((0, 1), a, b)
