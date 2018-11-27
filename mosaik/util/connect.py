"""
This module contains utility functions for connecting simulation models.
"""

import random


def connect_many_to_one(world, src_set, dest, *attrs, async_requests=False):
    """
    :meth:`~mosaik.scenario.World.connect` each entity in *src_set*
    to *dest*.

    See the :meth:`~mosaik.scenario.World.connect` for more details.
    """
    for src in src_set:
        world.connect(src, dest, *attrs, async_requests=async_requests)


def connect_randomly(world, src_set, dest_set, *attrs, evenly=True,
                     max_connects=float('inf')):
    """
    Randomly :meth:`~mosaik.scenario.World.connect` the entities from
    *src_set* to the entities from *dest_set* and return a subset of *dest_set*
    containing all entities with a connection.

    *world* is an instance of the :class:`~mosaik.scenario.World` to which the
    entities belong.

    *src_set* and *dest_set* are iterables containing
    :class:`~mosaik.scenario.Entity` instances. *src_set* may be empty,
    *dest_set* must not be empty. Each entity of *src_set* will be connected to
    an entity of *dest_set*, but not every entity of *dest_set* will
    necessarily have a connection (e.g., if you connect a set of three entities
    to a set of four entities). A set of all entities from *dest_set*, to which
    at least one entity from *src_set* was connected, will be returned.

    *attrs* is a list of attribute names of pairs as in
    :meth:`~mosaik.scenario.World.connect()`.

    If the flag *evenly* is set to ``True``, entities connections will be
    distributed as evenly as possible. That means if you connect a set of three
    entities to a set of three entities, there will be three 1:1 connections;
    if you connect four entities to three entities, there will be one 2:1 and
    two 1:1 connections. If *evenly* is set to ``False``, connections will be
    truly random. That means if you connect three entities to three entities,
    you may either have three 1:1 connections, one 2:1 and two 1:1 connections
    or just one 3:1 connection.

    *max_connects* lets you set the maximum number of connections that an
    entity of *dest_set* may receive. This argument is only taken into account
    if *evenly* is set to ``False``.
    """
    dest_set = list(dest_set)
    assert dest_set

    if evenly:
        connected = _connect_evenly(world, src_set, dest_set, *attrs)
    else:
        connected = _connect_randomly(world, src_set, dest_set, *attrs,
                                      max_connects=max_connects)

    return connected


def _connect_evenly(world, src_set, dest_set, *attrs):
    connect = world.connect
    connected = set()

    src_size, dest_size = len(src_set), len(dest_set)
    pos = 0
    while pos < src_size:
        random.shuffle(dest_set)
        for src, dest in zip(src_set[pos:], dest_set):
            connect(src, dest, *attrs)
            connected.add(dest)
        pos += dest_size

    return connected


def _connect_randomly(world, src_set, dest_set, *attrs,
                      max_connects=float('inf')):
    connect = world.connect
    connected = set()

    assert len(src_set) <= (len(dest_set) * max_connects)
    max_i = len(dest_set) - 1
    randint = random.randint
    connects = {}
    for src in src_set:
        i = randint(0, max_i)
        dest = dest_set[i]
        connect(src, dest, *attrs)
        connected.add(dest)
        connects[dest] = connects.get(dest, 0) + 1
        if connects[dest] >= max_connects:
            dest_set.remove(dest)
            max_i -= 1
            assert max_i >= 0

    return connected
