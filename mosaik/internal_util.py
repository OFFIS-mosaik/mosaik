from typing import Callable, Dict
from typing_extensions import TypeVar

from importlib import metadata

K = TypeVar("K")
V = TypeVar("V")


def recursive_merge_existing(
    merger: Callable[[V, V], V],
    target: Dict[K, V],
    other: Dict[K, V],
) -> Dict[K, V]:
    for k, v in target.items():
        if k in other:
            target[k] = merger(v, other[k])
    return target


def recursive_merge_all(
    merger: Callable[[V, V], V],
    target: Dict[K, V],
    other: Dict[K, V],
) -> Dict[K, V]:
    for k, v in other.items():
        if k in target:
            target[k] = merger(target[k], v)
        else:
            target[k] = v
    return target

def doc_link(page: str, anchor: str) -> str:
    version = metadata.version("mosaik")
    return f"https://mosaik.readthedocs.io/en/{version}/{page}.html#{anchor}"