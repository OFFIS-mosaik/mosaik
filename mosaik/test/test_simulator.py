from unittest import mock

import pytest
import simpy

from mosaik import scenario, simulator, simmanager


@pytest.fixture
def env():
    env = scenario.Environment({})
    env.simpy_env = simpy.Environment()
    env.sims = {i: simmanager.SimProxy(i, mock.Mock()) for i in range(4)}
    env.df_graph.add_edges_from([(0, 2), (1, 2), (2, 3)])
    env.df_graph[0][2]['wait_event'] = simulator.WaitEvent(env.simpy_env, 1)
    return env


def test_run():
    """Test if a process is started for every simulatin."""
    def dummy_proc(env, sim, until):
        sim.proc_started = True
        yield env.simpy_env.timeout(until)

    class Sim:
        proc_started = False

    env = scenario.Environment({})
    env.sims = {i: Sim() for i in range(2)}

    until = 2
    with mock.patch('mosaik.simulator.sim_process', dummy_proc):
        simulator.run(env, until)

    for sim in env.sims.values():
        assert sim.proc_started
    assert env.simpy_env.now == until


def test_sim_process():
    """``sim_process()`` is tested via test_mosaik.py."""
    assert True


def test_step_required(env):
    """Test *step_required is True*, becauce a simulator is waiting for us."""
    evt = simulator.step_required(env, env.sims[0])
    assert evt.triggered


def test_step_not_required(env):
    """Test *step_required is False*, because noone is waiting for us."""
    evt = simulator.step_required(env, env.sims[1])
    assert not evt.triggered

    evt = simulator.step_required(env, env.sims[2])
    assert not evt.triggered


def test_step_required_no_successors(env):
    """Test *step_required is True*, because there is noone that could be
    waiting for us."""
    evt = simulator.step_required(env, env.sims[3])
    assert evt.triggered


def test_wait_for_dependencies(env):
    """Test waiting for dependencies and triggering them."""
    for i in range(2):
        env.sims[i].step_required = env.simpy_env.event()
        if i == 0:
            env.sims[i].step_required.succeed()
    evt = simulator.wait_for_dependencies(env, env.sims[2])
    assert len(evt._events) == 2
    assert not evt.triggered
    for i in range(2):
        assert env.sims[i].step_required.triggered


def test_wait_for_dependencies_all_done(env):
    """All dependencies already stepped far enough. No waiting required."""
    env._df_cache = {0: {0: [], 1: []}}
    evt = simulator.wait_for_dependencies(env, env.sims[2])
    assert len(evt._events) == 0
    assert evt.triggered


def test_get_input_data(env):
    """Simple test for get_input_data()."""
    env._df_cache = {0: {
        0: {'1': {'x': 0, 'y': 1}},
        1: {'2': {'x': 2, 'z': 4}},
    }}
    env.df_graph[0][2]['dataflows'] = [('1', '0', [('x', 'in')])]
    env.df_graph[1][2]['dataflows'] = [('2', '0', [('z', 'in')])]
    data = simulator.get_input_data(env, env.sims[2])
    assert data == {'0': {'in': [0, 4]}}


def test_step(env):
    inputs = object()
    sim = env.sims[0]
    sim.inst.step.return_value = 1
    assert (sim.last_step, sim.next_step) == (float('-inf'), 0)

    evt = simulator.step(env, sim, inputs)
    assert evt.triggered
    assert (sim.last_step, sim.next_step) == (0, 1)
    assert sim.inst.step.call_args == mock.call(0, inputs)


def test_get_outputs(env):
    env._df_cache[0] = {'spam': 'eggs'}
    env._df_cache[1] = {'foo': 'bar'}
    env._df_outattr[0][0] = ['x', 'y']
    wait_event = simulator.WaitEvent(env.simpy_env, 2)
    env.df_graph[0][2]['wait_event'] = wait_event
    sim = env.sims[0]
    sim.inst.get_data.return_value = {'0': {'x': 0, 'y': 1}}
    sim.last_step, sim.next_step = 0, 1

    evt = simulator.get_outputs(env, sim)
    assert evt.triggered
    assert not wait_event.triggered
    assert 'wait_event' in env.df_graph[0][2]
    assert env._df_cache == {
        0: {'spam': 'eggs', 0: {'0': {'x': 0, 'y': 1}}},
        1: {'foo': 'bar'},
    }

    for s in env.sims.values():
        s.last_step, s.next_step = 1, 2
    sim.last_step, sim.next_step = 2, 3
    evt = simulator.get_outputs(env, sim)
    assert evt.triggered
    assert wait_event.triggered
    assert 'wait_event' not in env.df_graph[0][2]
    assert env._df_cache == {
        2: {0: {'0': {'x': 0, 'y': 1}}},
    }


def test_get_progress():
    class Sim:
        def __init__(self, time):
            self.next_step = time

    sims = {i: Sim(0) for i in range(2)}
    assert simulator.get_progress(sims, 4) == 0

    sims[0].next_step = 1
    assert simulator.get_progress(sims, 4) == 12.5

    sims[0].next_step = 2
    assert simulator.get_progress(sims, 4) == 25

    sims[1].next_step = 3
    sims[0].next_step = 3
    assert simulator.get_progress(sims, 4) == 75

    sims[0].next_step = 4
    sims[1].next_step = 6
    assert simulator.get_progress(sims, 4) == 100
