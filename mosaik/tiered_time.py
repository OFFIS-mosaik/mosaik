from __future__ import annotations

from dataclasses import dataclass
import functools
from typing import Set


def tuple_add(xs: tuple[int, ...], ys: tuple[int, ...]) -> tuple[int, ...]:
    return tuple(x + y for x, y in zip(xs, ys))


@dataclass(frozen=True)
class TieredDuration:
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

    def __add__(self, other: TieredDuration) -> TieredDuration:
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
        return TieredDuration(*tiers, pre_length=self.pre_length, cutoff=cutoff)

    def __le__(self, other: TieredDuration) -> bool:
        assert len(self) == len(other)
        assert self.pre_length == other.pre_length
        joint_cutoff = min(self.cutoff, other.cutoff)
        if self.tiers[0:joint_cutoff] < other.tiers[0:joint_cutoff]:
            return True
        return self.tiers <= other.tiers and self.cutoff <= other.cutoff

    def __lt__(self, other: TieredDuration) -> bool:
        return self <= other and not self == other

    def __ge__(self, other: TieredDuration) -> bool:
        return other <= self

    def __gt__(self, other: TieredDuration) -> bool:
        return other < self

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

    def __add__(self, interval: TieredDuration) -> TieredTime:
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


class MinimalDurations:
    durations: Set[TieredDuration]
    """All the minimal durations. Invariant: No two durations in this
    set are comparable.
    """

    def __init__(self):
        self.durations = set()

    def insert(self, duration: TieredDuration):
        displaced_durations: Set[TieredDuration] = set()
        for existing_duration in self.durations:
            if duration < existing_duration:
                displaced_durations.add(existing_duration)
            if existing_duration <= duration:
                # Because of the invariant of self.durations, we don't
                # insert duration, and no other existing_duration can be
                # displaced by duration
                return
        self.durations.difference_update(displaced_durations)
        self.durations.add(duration)
