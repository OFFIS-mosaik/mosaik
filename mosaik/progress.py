import asyncio
from loguru import logger
from typing import Generic, Optional, Protocol, Self, TypeVar

class Comparable(Protocol):
    def __lt__(self, other: Self) -> bool: ...
    def __ge__(self, other: Self) -> bool: ...

T = TypeVar('T', bound=Comparable)

class Progress(Generic[T]):
    """A progress keeps track of a simulator's progress and provided
    coroutines for waiting for the progress to reach or pass a given
    value.
    
    The implemenation is generic over the type of the time values,
    provided that they are comparable.
    """
    value: T
    """The current value of the progress."""
    _futures: list[tuple[T, bool, asyncio.Future[T]]]
    """Futures representing all currently waiting has_reached and
    has_passed calls.

    The components of each tuple are the trigger time, a bool
    specifying whether the time needs to be passed (True) or just
    reached (False), and the ``Future`` to trigger upon passing/
    reaching the time.
    """
    
    def __init__(self, initial: T):
        self._futures = []
        self.value = initial

    def set(self, value: T):
        """Set the progress to ``value`` and trigger all waiting
        coroutines whose wait times have now been passed or reached.
        """
        assert value >= self.value, "cannot progress backwards"
        self.value = value
        # Use index-based for loop so we can call del in the loop.
        for index in reversed(range(0, len(self._futures))):
            time, needs_to_pass, future = self._futures[index]
            if needs_to_pass and time < value:
                if not future.cancelled():
                    future.set_result(value)
                del self._futures[index]
            if not needs_to_pass and time <= value:
                if not future.cancelled():
                    future.set_result(value)
                del self._futures[index]

    async def has_reached(self, time: T) -> T:
        """Wait until this ``Progress`` has reached (or passed) the
        given time. Returns immediately if this ``Progress`` has
        already reached (or passed) the given time.
        
        :param time: the time that needs to be reached (or passed)
        :returns: the actual value of the progress when the given
        time has been reached or passed
        """
        if self.value >= time:
            return self.value
        future: asyncio.Future[T] = asyncio.Future()
        self._futures.append((time, False, future))
        return await future

    async def has_passed(self, time: T) -> T:
        """Wait until this ``Progress`` has passed the given time.
        Returns immediately if this ``Progress`` has already passed
        the given time.
        
        :param time: the time that needs to be passed
        :returns: the actual value of the progress when the given
        time has been passed
        """
        if self.value > time:
            return self.value
        future: asyncio.Future[T] = asyncio.Future()
        self._futures.append((time, True, future))
        return await future
        
