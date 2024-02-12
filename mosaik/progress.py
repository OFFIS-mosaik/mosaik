from __future__ import annotations

import asyncio
from loguru import logger  # type: ignore  # noqa: F401
from typing import List, Tuple

from mosaik.tiered_time import TieredInterval, TieredTime


class Progress:
    """A progress keeps track of a simulator's progress and provided
    coroutines for waiting for the progress to reach or pass a given
    value.
    
    The implemenation is generic over the type of the time values,
    provided that they are comparable.
    """
    time: TieredTime
    """The current value of the progress."""
    _futures: List[Tuple[TieredTime, TieredInterval, bool, asyncio.Future[TieredTime]]]
    """Futures representing all currently waiting has_reached and
    has_passed calls.

    The components of each tuple are the trigger time, a bool
    specifying whether the time needs to be passed (True) or just
    reached (False), and the ``Future`` to trigger upon passing/
    reaching the time.
    """
    
    def __init__(self, initial: TieredTime):
        self._futures = []
        self.time = initial

    def set(self, time: TieredTime):
        """Set the progress to ``value`` and trigger all waiting
        coroutines whose wait times have now been passed or reached.
        """
        assert time >= self.time, "cannot progress backwards"
        self.time = time
        # Use index-based for loop so we can call del in the loop.
        for index in reversed(range(0, len(self._futures))):
            target, shift, needs_to_pass, future = self._futures[index]
            time_at_dest = time + shift
            if needs_to_pass and time_at_dest > target:
                if not future.cancelled():
                    future.set_result(time_at_dest)
                del self._futures[index]
            if not needs_to_pass and time_at_dest >= target:
                if not future.cancelled():
                    future.set_result(time_at_dest)
                del self._futures[index]

    async def has_reached(self, target: TieredTime, shift: TieredInterval | None = None) -> TieredTime:
        """Wait until this ``Progress`` has reached (or passed) the
        given time. Returns immediately if this ``Progress`` has
        already reached (or passed) the given time.
        
        :param time: the time that needs to be reached (or passed)
        :returns: the actual value of the progress when the given
        time has been reached or passed
        """
        if shift is None:
            shift = TieredInterval(len(target), len(target), (0,) * len(target))
        # TODO: Remove duplication of this check with the one in `set`
        if self.time + shift >= target:
            return self.time
        future: asyncio.Future[TieredTime] = asyncio.Future()
        self._futures.append((target, shift, False, future))
        return await future

    async def has_passed(self, target: TieredTime, shift: TieredInterval | None = None) -> TieredTime:
        """Wait until this ``Progress`` has passed the given time.
        Returns immediately if this ``Progress`` has already passed
        the given time.
        
        :param time: the time that needs to be passed
        :returns: the actual value of the progress when the given
        time has been passed
        """
        if shift is None:
            shift = TieredInterval(len(target), len(target), (0,) * len(target))
        # TODO: Remove duplication of this check with the one in `set`
        if self.time + shift > target:
            return self.time
        future: asyncio.Future[TieredTime] = asyncio.Future()
        self._futures.append((target, shift, True, future))
        return await future

    def __repr__(self) -> str:
        return f"<Progress at {self.time!r} with {len(self._futures)} waiting>"
        
