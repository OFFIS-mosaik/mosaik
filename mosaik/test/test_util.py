from unittest import mock

from simpy.io.network import RemoteException
import pytest

from mosaik import scenario, util


def test_ordered_default_dict():
    d = util.OrderedDefaultdict(list)
    for i in [3, 0, 4, 1, 2]:
        for j in range(2):
            d[i].append(i * j)
    assert list(d.items()) == [
        (3, [0, 3]),
        (0, [0, 0]),
        (4, [0, 4]),
        (1, [0, 1]),
        (2, [0, 2]),
    ]

    d = util.OrderedDefaultdict()
    with pytest.raises(KeyError):
        d[1].append(2)

    pytest.raises(TypeError, util.OrderedDefaultdict, 3)


@pytest.mark.parametrize(['error', 'errmsg'], [
    (ConnectionResetError(),
     'ERROR: Spam\nMosaik terminating\n'),
    (RemoteException('spam', 'eggs'),
     'RemoteException:\neggs\n————————————————\nMosaik terminating\n'),

])
def test_sync_process_error(error, errmsg, capsys):
    """Test sims breaking during their start."""
    world = scenario.World({})

    def gen():
        yield world.env.event()

    with mock.patch.object(world.env, 'run', side_effect=error):
        pytest.raises(SystemExit, util.sync_process, gen(), world, 'Spam')

    world.shutdown()

    out, err = capsys.readouterr()
    assert out == errmsg
    assert err == ''
