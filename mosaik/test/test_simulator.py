from unittest import mock

import pytest

from mosaik import scenario, simulator


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


@pytest.mark.xfail
def test_sim_process():
    assert 0


@pytest.mark.xfail
def test_wait_for_dependencies():
    assert 0


@pytest.mark.xfail
def test_step():
    assert 0


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
