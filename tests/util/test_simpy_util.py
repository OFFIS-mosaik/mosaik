import pytest
from simpy.io.network import RemoteException

import mosaik.util
from mosaik import exceptions, scenario
from mosaik.util.simpy import sync_process


@pytest.mark.parametrize(['error', 'errmsg'], [
    (ConnectionResetError('Spam'),
     'ERROR: Spam\nMosaik terminating\n'),
    (RemoteException('spam', 'eggs'),
     'RemoteException:\neggs\n————————————————\nMosaik terminating\n'),
    (exceptions.SimulationError('spam'),
     'ERROR: spam\nMosaik terminating\n'),

])
def test_sync_process_error(error, errmsg, capsys):
    """
    Test sims breaking during their start.
    """
    world = scenario.World({})

    def gen():
        raise error
        yield world.env.event()

    pytest.raises(SystemExit, mosaik.util.simpy.sync_process, gen(), world)

    out, err = capsys.readouterr()
    assert out == errmsg
    assert err == ''


def test_sync_process_errback():
    world = scenario.World({})
    try:
        test_list = []
        cb = lambda: test_list.append('got called')  # flake8: noqa

        def gen():
            raise ConnectionError()
            yield world.env.event()

        sync_process(gen(), world, errback=cb, ignore_errors=True)
        assert test_list == ['got called']
    finally:
        world.shutdown()


def test_sync_process_ignore_errors():
    world = scenario.World({})

    def gen():
        raise ConnectionError()
        yield world.env.event()

    sync_process(gen(), world, ignore_errors=True)
