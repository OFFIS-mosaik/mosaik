from __future__ import annotations

import functools
from dataclasses import dataclass
from typing import Any, Optional, Set, Union


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
    """A set of minimal TieredDurations.

    Because tiered durations are not always comparable, a set of them
    does not always have a unique minimum. (However, for a given length
    and pre-length, the number of minimal elements is at most
    min(length, pre-length).)

    This class represents a set of minimal elements. In other words, the
    elements of `durations` are pairwise incomparable. When a new
    duration is `insert`ed, `durations` will be updated to contain the
    minimal elements among all elements seen so far.
    """

    durations: Set[TieredDuration]
    """All the minimal durations. Invariant: No two durations in this
    set are comparable.
    """

    def __init__(self, duration: Optional[TieredDuration] = None):
        self.durations = set()
        if duration is not None:
            self.durations.add(duration)

    def insert(self, duration: TieredDuration) -> bool:
        """
        Insert a `TieredDuration` into the minimal duration set. If the
        new duration is bigger than any existing one, nothing happens.
        Otherwise, all exisiting durations that are bigger than the new
        one are removed and the new one is added to the set.
        (Incomparable existing duration are not touched.)

        Returns whether the set of durations was changed.
        """
        displaced_durations: Set[TieredDuration] = set()
        for existing_duration in self.durations:
            if duration < existing_duration:
                displaced_durations.add(existing_duration)
            if existing_duration <= duration:
                # Because of the invariant of `self.durations`, we don't
                # insert `duration`, and no other `existing_duration`
                # can be displaced by `duration`.
                return False
        self.durations.difference_update(displaced_durations)
        self.durations.add(duration)
        return True

    def insert_all(self, other: MinimalDurations) -> bool:
        updated = False
        for duration in other.durations:
            updated = self.insert(duration) or updated
        return updated

    def __add__(
        self, other: Union[MinimalDurations, TieredDuration]
    ) -> MinimalDurations:
        result = MinimalDurations()
        if isinstance(other, TieredDuration):
            other = MinimalDurations(other)
        for u in self.durations:
            for v in other.durations:
                result.insert(u + v)
        return result

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, MinimalDurations):
            raise TypeError("cannot compare MinimalDurations to values of other types")
        return self.durations == other.durations

    def contains_zero(self) -> bool:
        return any(all(t == 0 for t in duration.tiers) for duration in self.durations)

    def is_time_shifted(self) -> bool:
        """Whether this MinimalDurations is time-shifted, i.e. there is
        a non-zero first component in any (equivalently, all) of its
        Durations.
        """
        return any(duration.tiers[0] > 0 for duration in self.durations)

    def is_weak(self) -> bool:
        """Whether this MinimalDurations is weak, i.e. not time-shifted
        but also not zero.
        """
        return not (self.contains_zero() or self.is_time_shifted())

    def earliest_sum(self, other: TieredTime) -> TieredTime:
        """Add `other` to all durations in this set and return the
        minimal result.
        """
        return min(other + duration for duration in self.durations)

    @classmethod
    def from_duration(cls, duration: TieredDuration) -> MinimalDurations:
        min_durations = MinimalDurations()
        min_durations.insert(duration)
        return min_durations
