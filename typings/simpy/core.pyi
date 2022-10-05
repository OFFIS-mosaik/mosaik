"""
This type stub file was generated by pyright.
"""

"""
Core components for event-discrete simulation environments.

"""
from typing import Any, Iterable, Iterator, Optional
import simpy.events



class BaseEnvironment:
    ...
    


class Environment(BaseEnvironment):
    def process(self, generator: Iterator[simpy.events.Event]) -> simpy.events.Process: ...
    def timeout(self, delay: float, value: Optional[Any]=None) -> simpy.events.Timeout: ...
    def event(self) -> simpy.events.Event: ...
    def all_of(self, events: Iterable[simpy.events.Event]) -> simpy.events.AllOf: ...
    def any_of(self, events: Iterable[simpy.events.Event]) -> simpy.events.AnyOf: ...



