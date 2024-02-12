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

    def __post_init__(self):
        assert self.cutoff <= self.pre_length
        assert self.cutoff <= len(self.tiers)
    
    def __len__(self) -> int:
        return len(self.tiers)
    
    @property
    def add(self) -> tuple[int, ...]:
        return self.tiers[0:self.cutoff]

    @property
    def ext(self) -> tuple[int, ...]:
        return self.tiers[self.cutoff:]
    
    def __add__(self, other: TieredInterval) -> TieredInterval:
        assert len(self) == other.pre_length
        add = tuple_add(self.add, other.add)
        if self.cutoff >= other.cutoff:
            ext = other.ext
        else:  # self.cutoff is shorter
            ext = tuple_add(self.ext + ((0,) * len(other.add)), other.add[self.cutoff:]) + other.ext
        tiers = add + ext
        cutoff = min(self.cutoff, other.cutoff)
        assert len(tiers) == len(other)
        return TieredInterval(self.pre_length, cutoff, tiers)

    def __lt__(self, other: TieredInterval):
        assert len(self) == len(other)
        assert self.pre_length == other.pre_length
        # Without this, comparison is not total, but it might still be
        # possible with more thought.
        assert self.cutoff == other.cutoff
        return self.tiers < other.tiers


@functools.total_ordering
@dataclass(frozen=True)
class TieredTime:
    tiers: tuple[int, ...]

    def __add__(self, interval: TieredInterval) -> TieredTime:
        assert len(self.tiers) == interval.pre_length
        return TieredTime(tuple_add(self.tiers, interval.add) + interval.ext)

    def __lt__(self, other: TieredTime) -> bool:
        assert len(self) == len(other)
        return self.tiers < other.tiers

    def __len__(self) -> int:
        return len(self.tiers)

    @property
    def time(self) -> int:
        return self.tiers[0]
