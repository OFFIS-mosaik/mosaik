import pytest

from mosaik import util


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
