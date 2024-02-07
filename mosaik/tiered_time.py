from __future__ import annotations

from dataclasses import dataclass


def tuple_add(xs: tuple[int, ...], ys: tuple[int, ...]) -> tuple[int, ...]:
    return tuple(x + y for x, y in zip(xs, ys))


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


@dataclass(frozen=True)
class TieredTime:
    tiers: tuple[int, ...]

    def __add__(self, interval: TieredInterval) -> TieredTime:
        assert len(self.tiers) == interval.pre_length
        return TieredTime(tuple_add(self.tiers, interval.add) + interval.ext)
