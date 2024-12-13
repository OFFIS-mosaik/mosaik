import platform
from typing import Callable, Dict

from typing_extensions import TypeVar

from mosaik._version import version

K = TypeVar("K")
V = TypeVar("V")


def merge_existing(
    merger: Callable[[V, V], V],
    target: Dict[K, V],
    other: Dict[K, V],
) -> Dict[K, V]:
    """Merge the values from ``other`` which correspond to keys that
    already exists in ``target`` into ``target`` (and return
    ``target``). The function ``merger`` will be used to combine the
    existing value and the new value from ``other``; this will often be
    another call to :fun:`merge_existing` to extend merging to several
    dict levels. If a key only exists in ``target``, its value will be
    kept. If a key only exists in ``other`` it will not appear in the
    result.
    """
    for k, v in target.items():
        if k in other:
            target[k] = merger(v, other[k])
    return target


def merge_all(
    merger: Callable[[V, V], V],
    target: Dict[K, V],
    other: Dict[K, V],
) -> Dict[K, V]:
    """Merge dict ``other`` into ``target``, which will be modified
    (and returned). If a key exists in both ``other`` and ``target``,
    the function ``merger`` will be called on the corresponding values
    to combine them. (In case of nested dictionaries, this will often
    be another call to :fun:`merge_all`). If only one of ``target``
    or ``other`` contains a key, the corresponding value will be used
    in the result.
    """
    for k, v in other.items():
        if k in target:
            target[k] = merger(target[k], v)
        else:
            target[k] = v
    return target


def doc_link(page: str, anchor: str) -> str:
    return f"https://mosaik.readthedocs.io/en/{version}/{page}.html#{anchor}"


def get_python_version():
    return platform.python_version()


def get_os():
    return platform.platform()
