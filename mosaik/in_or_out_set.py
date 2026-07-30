from __future__ import annotations

from collections.abc import Iterable


class OutSet[E]:
    """An OutSet[E] represents all elements of the type E except for a
    finite number.

    In particular, ``x in OutSet(elems)`` is ``True`` whenever
    ``x not in elems``. Set operations between instances of
    :class:`OutSet` and normal :class:`~frozenset` work as excepted.

    Note that by their nature it is not possible to iterate over an
    OutSet.
    """

    _set: frozenset[E]

    def __init__(self, elems: Iterable[E] = ()):
        self._set = frozenset(elems)

    def __sub__(self, other: InOrOutSet[E]) -> InOrOutSet[E]:
        if isinstance(other, OutSet):
            return other._set - self._set
        else:
            return OutSet(self._set | other)

    def __rsub__(self, rother: frozenset[E]) -> frozenset[E]:
        return rother & self._set

    def __and__(self, other: InOrOutSet[E]) -> InOrOutSet[E]:
        if isinstance(other, OutSet):
            return OutSet(self._set | other._set)
        else:
            return other - self._set

    def __rand__(self, rother: frozenset[E]) -> frozenset[E]:
        return rother - self._set

    def __or__(self, other: InOrOutSet[E]) -> OutSet[E]:
        if isinstance(other, OutSet):
            return OutSet(self._set & other._set)
        else:
            return OutSet(self._set - other)

    def __ror__(self, rother: frozenset[E]) -> OutSet[E]:
        return OutSet(self._set - rother)

    def __contains__(self, item: E) -> bool:
        return item not in self._set

    def __eq__(self, other: object):
        if not isinstance(other, OutSet):
            return False
        return self._set == other._set  # type: ignore  (Pyright does not know E here)

    def __str__(self):
        return f"OutSet({{{', '.join(map(str, self._set))}}})"


type InOrOutSet[E] = frozenset[E] | OutSet[E]
"""A InOrOutSet is either a FrozenSet or an OutSet. This means
that it can represent either
- a finite number of elements of the type E or
- all but a finite number of element of the type E.

Standard set-theoretic operations (union, intersection, etc.) can still
be computed for InOrOutSets and will result in a InOrOutSet again.
"""


def parse_set_triple[E](
    union: InOrOutSet[E] | None,
    part_a: InOrOutSet[E] | None,
    part_b: InOrOutSet[E] | None,
    union_name: str = "union",
    part_a_name: str = "part_a",
    part_b_name: str = "part_b",
) -> tuple[InOrOutSet[E], InOrOutSet[E]]:
    """Take three sets and make sure that the first is the disjoint
    union of the other two. If one of the sets is None, find the value
    for it that ensures this, if possible.
    Return the two parts.
    """
    missing_value_error = ValueError(
        f"at least two of {union_name}, {part_a_name} and {part_b_name} must be given"
    )

    if union is None:
        if part_a is not None and part_b is not None:
            union = part_a | part_b
        else:
            raise missing_value_error

    if part_a is None:
        if part_b is not None:
            part_a = union - part_b
        else:
            raise missing_value_error

    if part_b is None:
        part_b = union - part_a

    if not part_a & part_b == frozenset():
        raise ValueError(
            f"{part_a_name} ({part_a}) and {part_b_name} ({part_b}) are not disjoint"
        )

    if not union == (part_a | part_b):
        raise ValueError(
            f"{part_a_name} ({part_a}) and {part_b_name} ({part_b}) must be subsets "
            f"of {union_name} ({union}), and they must have {union_name} as their "
            f"union if both given"
        )

    return part_a, part_b


def wrap_set[E](set: Iterable[E] | OutSet[E] | None) -> InOrOutSet[E] | None:
    """Wrap an iterable or OutSet, resulting in an InOrOutSet. Pass
    through None unchanged.
    """
    if set is None or isinstance(set, OutSet):
        return set
    return frozenset(set)
