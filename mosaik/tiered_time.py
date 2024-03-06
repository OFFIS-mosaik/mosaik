from __future__ import annotations

from dataclasses import dataclass
import functools


def tuple_add(xs: tuple[int, ...], ys: tuple[int, ...]) -> tuple[int, ...]:
    return tuple(x + y for x, y in zip(xs, ys))


@functools.total_ordering
@dataclass(frozen=True)
class TieredInterval:
    pre_length: int
    cutoff: int
    tiers: tuple[int, ...]

    def __init__(
        self, *tiers: int, cutoff: int | None = None, pre_length: int | None = None
    ):
        if cutoff is None:
            cutoff = len(tiers)
        if pre_length is None:
            pre_length = cutoff
        assert cutoff >= 1
        assert cutoff <= pre_length
        assert cutoff <= len(tiers)
        object.__setattr__(self, "pre_length", pre_length)
        object.__setattr__(self, "cutoff", cutoff)
        object.__setattr__(self, "tiers", tiers)

    def __len__(self) -> int:
        return len(self.tiers)

    @property
    def add(self) -> tuple[int, ...]:
        return self.tiers[0 : self.cutoff]

    @property
    def ext(self) -> tuple[int, ...]:
        return self.tiers[self.cutoff :]

    def __add__(self, other: TieredInterval) -> TieredInterval:
        assert len(self) == other.pre_length
        add = tuple_add(self.add, other.add)
        if self.cutoff >= other.cutoff:
            ext = other.ext
        else:  # self.cutoff is shorter
            ext = (
                tuple_add(self.ext + ((0,) * len(other.add)), other.add[self.cutoff :])
                + other.ext
            )
        tiers = add + ext
        cutoff = min(self.cutoff, other.cutoff)
        assert len(tiers) == len(other)
        return TieredInterval(*tiers, pre_length=self.pre_length, cutoff=cutoff)

    def __lt__(self, other: TieredInterval):
        assert len(self) == len(other)
        assert self.pre_length == other.pre_length
        for i, (s, o) in enumerate(zip(self.tiers, other.tiers)):
            s_add_o_ext = other.cutoff <= i < self.cutoff
            o_add_s_ext = self.cutoff <= i < other.cutoff
            if s < o:
                if s_add_o_ext:
                    assert False, f"{self} and {other} are incomparable"
                return True
            if o > s:
                if o_add_s_ext:
                    assert False, f"{self} and {other} are incomparable"
                return False
        return False

    def __repr__(self):
        return (
            f"{':'.join(map(str, self.add))}|{':'.join(map(str, self.ext))}"
            f"({self.pre_length})"
        )


@functools.total_ordering
@dataclass(frozen=True)
class TieredTime:
    tiers: tuple[int, ...]

    def __init__(self, *tiers: int):
        object.__setattr__(self, "tiers", tiers)

    def __add__(self, interval: TieredInterval) -> TieredTime:
        assert len(self.tiers) == interval.pre_length
        return TieredTime(*(tuple_add(self.tiers, interval.add) + interval.ext))

    def __lt__(self, other: TieredTime) -> bool:
        assert len(self) == len(other)
        return self.tiers < other.tiers

    def __len__(self) -> int:
        return len(self.tiers)

    @property
    def time(self) -> int:
        return self.tiers[0]

    def __repr__(self):
        return f"{':'.join(map(str, self.tiers))}"
