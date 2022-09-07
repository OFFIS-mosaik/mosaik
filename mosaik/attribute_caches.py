from __future__ import annotations

from sortedcontainers import SortedDict
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Generic, Optional, Tuple, TypeVar
    from _typeshed import SupportsAllComparisons


V = TypeVar("V")
T = TypeVar("T", bound=SupportsAllComparisons)


class OutputCache(Generic[T, V]):
    """
    A storage class for a simulator's output (for a single attribute).
    """

    _cache: SortedDict
    """
    The values, keyed by their time.

    Since this is a SortedDict, we can get the index of the newest value that is
    not newer than t by calling `self._cache.bisect_right(t) - 1`. (We need to
    adjust the value by 1 because `bisect_right` returns the position where `t`
    would need to be inserted.)
    """
    _newest_access: Optional[T]
    """
    The newest time of access, used to prevent overwriting previously read data.
    """

    def __init__(self):
        self._cache = SortedDict()
        self._newest_access = None

    def add(self, time: T, data: V, allow_same_time_overwrite: bool = True):
        """
        Add data `data` to the cache for time `time`.

        This data will be returned for all `get` calls for times between `time`
        and the next time added to this buffer. If newer data exists, this will
        throw an exception to prevent causality errors.

        :param time: The time for the data.
        :param data: The cached data.
        :param allow_same_time_overwrite: (default `True`) controls
        whether overwriting the data for the newest time step is permissible.
        (This might be necessary for same-time loops.)

        :raises Exception: when attempting to insert data between existing
        data points or data that would invalidate data that has already been
        read.
        """
        if not self._newest_access:
            self._cache[time] = data
            return

        if self._newest_access < time or (
            self._newest_access == time and allow_same_time_overwrite
        ):
            self._cache[time] = data
        else:
            raise ValueError(
                f"Cannot add data at time {time} because newer data from time "
                f"{self._newest_access} exists."
            )

        self._newest_access = time

    def get(self, time: T) -> V:
        """
        Get the data for time `time`.

        This is the newest data in this collection
        with a time `<= time`. Also makes sure that data for earlier times
        can't be added after this (to prevent causality errors).

        :param time: The time for which data is requested.

        :raises Exception: when trying to access data from an empty collection
        or from time steps that have already been pruned.
        """
        return self.get_with_time(time)[1]

    def get_with_time(self, time: T) -> Tuple[T, V]:
        """
        Get the time and data for time `time`.

        The returned time will be the actual time for which the data was
        written, i.e. it will be earlier than the input time if no data for the
        input time exists.

        Behaves like ``get`` in all other regards.
        """
        # `bisect_right` gives the index that `time` would get if inserted into
        # the cache. We want the newest entry at least at old as `time`, i.e.
        # the value to the left of this index, hence the `-1`.
        index = self._cache.bisect_right(time) - 1
        if index < 0:
            raise KeyError("Trying to access expired data")

        time, data = self._cache.peekitem(index)
        if self._newest_access is None or time >= self._newest_access:
            self._newest_access = time
        return time, data

    def prune(self, time: T):
        """
        Remove all cached data that is not needed anymore at the given time.

        Data is not needed anymore if it won't be returned by `get` calls
        with times earlier than `time`.

        :param time: The oldest time for which `get` calls will be valid after
        this.
        """
        while len(self._cache) >= 2 and self._cache.peekitem(1)[0] <= time:
            self._cache.popitem(0)

    def __bool__(self):
        return bool(self._cache)


class PersistentInput(Generic[T, V]):
    _output: OutputCache[T, V]

    def __init__(self, output: OutputCache[T, V]):
        self._output = output

    def get(self, time: T):
        self._output.get(time)


class NonPersistentInput(Generic[T, V]):
    _output: OutputCache[T, V]
    _last_access: Optional[T]

    def __init__(self, output: OutputCache[T, V]) -> None:
        super().__init__()
        self._output = output
        self._last_access = None

    def get(self, time: T) -> Optional[V]:
        """Only return each value once."""
        value_time, value = self._output.get_with_time(time)
        if self._last_access != value_time:
            self._last_access = value_time
            return value
        else:
            return None
