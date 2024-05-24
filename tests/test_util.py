import collections
import pytest
import random

from mosaik import util


class World(object):
    """
    A dummy world for testing purposes.
    """
    def __init__(self):
        self.src_connects = set()
        self.dest_connects = collections.defaultdict(lambda: 0)
        self.async_requests = None

    def connect(self, src, dest, *attr_pairs, async_requests=False):
        self.async_requests = async_requests
        self.src_connects.add(src)
        self.dest_connects[dest] += 1


def test_connect_many_to_one():
    world = World()
    src_set = [object() for i in range(3)]
    dest = object()

    util.connect_many_to_one(world, src_set, dest, 'a', 'b',
                             async_requests=True)

    assert world.async_requests is True
    assert world.src_connects == set(src_set)
    assert world.dest_connects == {dest: len(src_set)}


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
    """
    Test if connect_randomly() connects the correct amount of entities.

    *src_size* and *dest_size* denote the size of the src/dest entity sets.

    *evenly* and *max_c* are passed as keyword arguments to the function.

    *dest_connects* is a ``(min, max)`` tuple describing how many entities of
    the dest set have at least or most to be connected.
    """
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
