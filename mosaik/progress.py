from __future__ import annotations

import asyncio
from typing import List, Tuple

from loguru import logger  # type: ignore  # noqa: F401

from mosaik.tiered_time import TieredDuration, TieredTime

TriggerSpec = Tuple[TieredTime, TieredDuration, bool]


class Progress:
    """A progress keeps track of a simulator's progress and provided
    coroutines for waiting for the progress to reach or pass a given
    value.

    The implemenation is generic over the type of the time values,
    provided that they are comparable.
    """

    time: TieredTime
    """The current value of the progress."""
    _futures: List[Tuple[TriggerSpec, asyncio.Future[TieredTime]]]
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
            trigger_spec, future = self._futures[index]
            triggered_time = self._triggered_time(trigger_spec)
            if triggered_time:
                if not future.cancelled():
                    future.set_result(triggered_time)
                del self._futures[index]

    def _triggered_time(self, trigger_spec: TriggerSpec) -> None | TieredTime:
        """Get the actual (destination) time at which ``trigger_spec``
        was triggered, or ``None`` if it has not been triggered yet.
        """
        target, shift, needs_to_pass = trigger_spec
        time_at_dest = self.time + shift
        if needs_to_pass and time_at_dest > target:
            return time_at_dest
        if not needs_to_pass and time_at_dest >= target:
            return time_at_dest
        return None

    async def _add_trigger(
        self, target: TieredTime, shift: TieredDuration | None, needs_to_pass: bool
    ) -> TieredTime:
        """Add a trigger to this progress. This gets called by
        ``has_reached`` and ``has_passed`` with ``needs_to_pass`` set to
        ``False`` or ``True``, respectively.
        """
        if shift is None:
            shift = TieredDuration(*((0,) * len(self.time)))
        trigger_spec = (target, shift, needs_to_pass)
        triggered_time = self._triggered_time(trigger_spec)
        if triggered_time:
            return triggered_time
        future: asyncio.Future[TieredTime] = asyncio.Future()
        self._futures.append((trigger_spec, future))
        return await future

    async def has_reached(
        self,
        target: TieredTime,
        shift: TieredDuration | None = None,
    ) -> TieredTime:
        """Wait until this ``Progress`` has reached (or passed) the
        given time. Returns immediately if this ``Progress`` has
        already reached (or passed) the given time.

        :param time: the time that needs to be reached (or passed)
        :returns: the actual value of the progress when the given
            time has been reached or passed
        """
        return await self._add_trigger(target, shift, False)

    async def has_passed(
        self,
        target: TieredTime,
        shift: TieredDuration | None = None,
    ) -> TieredTime:
        """Wait until this ``Progress`` has passed the given time.
        Returns immediately if this ``Progress`` has already passed
        the given time.

        :param time: the time that needs to be passed
        :return: the actual value of the progress when the given
            time has been passed
        """
        return await self._add_trigger(target, shift, True)

    def __repr__(self) -> str:
        return f"<Progress at {self.time!r} with {len(self._futures)} waiting>"


class ProgressProxy:
    def __init__(self, progress: Progress):
        self._progress = progress

    async def has_reached(self, target: int) -> int:
        tiered_target = TieredTime(target)
        current_step = await self._progress.has_reached(tiered_target, None)
        return current_step.time

    async def has_passed(self, target: int) -> int:
        tiered_target = TieredTime(target)
        current_step = await self._progress.has_passed(tiered_target, None)
        return current_step.time
