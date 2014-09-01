import collections
import random

from simpy.io.network import RemoteException
import pytest

from mosaik import exceptions, scenario, util


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
    (ConnectionResetError('Spam'),
     'ERROR: Spam\nMosaik terminating\n'),
    (RemoteException('spam', 'eggs'),
     'RemoteException:\neggs\n————————————————\nMosaik terminating\n'),
    (exceptions.SimulationError('spam'),
     'ERROR: spam\nMosaik terminating\n'),

])
def test_sync_process_error(error, errmsg, capsys):
    """Test sims breaking during their start."""
    world = scenario.World({})

    def gen():
        raise error
        yield world.env.event()

    pytest.raises(SystemExit, util.sync_process, gen(), world)

    world.shutdown()

    out, err = capsys.readouterr()
    assert out == errmsg
    assert err == ''


def test_sync_process_ignore_errors():
    world = scenario.World({})

    def gen():
        raise ConnectionError()
        yield world.env.event()

    util.sync_process(gen(), world, ignore_errors=True)


@pytest.mark.parametrize(['src_size', 'dest_size', 'evenly', 'max_c',
                          'dest_connects'], [
    (20, 20, True, None, (1, 1)),
    (0,  20, True, None, (0, 0)),
    (12, 20, True, None, (0, 1)),
    (20, 12, True, None, (1, 2)),
    (20,  1, True, None, (20, 20)),
    (42, 20, True, None, (2, 3)),
    (20, 20, False, float('inf'), (0, 20)),
    (0,  20, False, float('inf'), (0, 0)),
    (12, 20, False, float('inf'), (0, 12)),
    (20, 12, False, float('inf'), (0, 20)),
    (20,  1, False, float('inf'), (20, 20)),
    (90, 20, False, float('inf'), (0, 90)),
    (90, 20, False, 6, (0, 6)),
])
def test_connect_randomly(src_size, dest_size, evenly, max_c, dest_connects):
    """Test if connect_randomly() connects the correct amount of entities.

    *src_size* and *dest_size* denote the size of the src/dest entity sets.

    *evenly* and *max_c* are passed as keyword arguments to the function.

    *dest_connects* is a ``(min, max)`` tuple describing how many entities of
    the dest set have at least or most to be connected.

    """
    class World:
        def __init__(self):
            self.src_connects = set()
            self.dest_connects = collections.defaultdict(lambda: 0)

        def connect(self, src, dest, *attr_pairs):
            self.src_connects.add(src)
            self.dest_connects[dest] += 1

    for seed in range(100):
        random.seed(seed)
        world = World()
        src_set = [object() for i in range(src_size)]
        dest_set = [object() for i in range(dest_size)]

        connected = util.connect_randomly(world, src_set, dest_set, 'a', 'b',
                                          evenly=evenly, max_connects=max_c)
        if evenly:
            assert len(connected) == min(src_size, dest_size)
        else:
            assert 0 <= len(connected) <= min(src_size, dest_size)

        assert len(world.src_connects) == src_size
        assert len(world.dest_connects) == len(connected)
        if src_size == 0:
            assert not world.dest_connects
        else:
            assert min(world.dest_connects.values()) >= dest_connects[0]
            assert max(world.dest_connects.values()) <= dest_connects[1]


def test_connect_randomly_errors():
    # dest_set is empty
    # dest_set too small for src_set and max_connects
    pass
