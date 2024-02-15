from __future__ import annotations

from dataclasses import dataclass
import functools


@functools.total_ordering
@dataclass(frozen=True)
class DenseTime:
    """A pair consisting of a time and a microstep. Microsteps are used
	to order events that happen at the same time.

	There is a slightly surprising definition of addition for these:
	.. math::
	    (t, m) + (t', m') = \\begin{cases}
			(t, m + m') & t' = 0 \\\\
	        (t + t', m') & t' \\neq 0
		\\end{cases}
	This prevents microsteps from accumulating across time steps.
	
	As this addition is not always invertible (:math:`m` is discarded
	if :math:`t' \\neq 0`), subtraction follows a “best effort”
	principle: :math:`\\beta - \\delta` is the earliest time
	:math:`\\alpha` such that :math:`\\alpha + \\delta` is
	:math:`\\beta` or later.

    To support usage in networkx algorithms, some methods also take
    ``int``s instead of ``DenseTime`` objects. An ``int`` ``a`` is
    interpreted as ``DenseTime(a, 0)`` in these cases.
	"""

    time: int
    microstep: int = 0

    def __post_init__(self):
        assert isinstance(self.time, int)
        assert isinstance(self.microstep, int)

    def __add__(self, other: DenseTime) -> DenseTime:
        # Giving an int as `other` is only here to support use in
        # networkx algorithms
        if isinstance(other, int):
            return self + DenseTime(other)

        if other.time == 0:
            return DenseTime(self.time, self.microstep + other.microstep)
        else:
            return DenseTime(self.time + other.time, other.microstep)

    def __radd__(self, other: int) -> DenseTime:
        # Adding to ints is only here to support use in  networkx
        # algorithms
        assert isinstance(other, int)
        return DenseTime(self.time + other, self.microstep)

    def __sub__(self, other: DenseTime) -> DenseTime:
        # dt_b - dt_delta should be the earliest DenseTime dt_a such
        # that dt_a + dt_delta is dt_b or later. (Due to the way that
        # DenseTime addition works, it is not always possible to
        # ensure dt_a + dt_delta = dt_b.)
        if other.time == 0:
            return DenseTime(self.time, self.microstep - other.microstep)
        elif other.microstep >= self.microstep:
            return DenseTime(self.time - other.time, 0)
        else:
            return DenseTime(self.time - other.time + 1, 0)

    def __lt__(self, other: DenseTime) -> bool:
        # Giving an int as `other` is only here to support use in
        # networkx algorithms
        if isinstance(other, int):
            return self.time < other

        return self.time < other.time or (
            self.time == other.time and self.microstep < other.microstep
        )

    def __str__(self):
        return f"{self.time}:{self.microstep}"

    @classmethod
    def parse(cls, input: str) -> DenseTime:
        try:
            time_str, microstep_str = input.split(":")
            return DenseTime(int(time_str), int(microstep_str))
        except ValueError:
            return DenseTime(int(input))
