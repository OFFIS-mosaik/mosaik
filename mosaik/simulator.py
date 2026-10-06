from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

import pyarrow as pa

from mosaik.tiered_time import TieredTime

type Time = TieredTime
type ModelName = str
type Attr = str

type MeasData = dict[ModelName, pa.RecordBatch]
"""Mapping model names to record batches with one row per entity of
that model and one column per attribute of that model.
"""


type EventData = dict[ModelName, dict[Attr, pa.RecordBatch]]
"""Mapping model names to record batches with the columns time, eidx,
and value, where time is a tuple of integers, eidx is the index of the
entity in the simulator and value is of a union type with one variant
per input event of this simulator.
"""


@dataclass
class ModelMeta:
    in_events: dict[Attr, pa.DataType]


@dataclass
class SimMeta:
    models: dict[ModelName, ModelMeta]


class Simulator(Protocol):
    @property
    def meta(self) -> SimMeta: ...
    async def setup_done(self) -> None: ...
    async def set_measurements(self, time: Time, measurements: MeasData): ...
    async def trigger(
        self, time: Time, events: EventData
    ) -> tuple[Time | None, EventData]: ...
    async def get_data(self, time: Time) -> MeasData: ...


class NoopSimulator:
    """A simulator that does nothing (as much as is possible).

    This is for testing.
    """

    async def setup_done(self) -> None:
        pass

    async def set_measurements(self, time: Time, measurements: MeasData) -> None:
        pass

    async def trigger(
        self, time: Time, events: EventData
    ) -> tuple[Time | None, EventData]:
        return (None, pa.RecordBatch.empty())

    async def get_data(self, time: Time) -> MeasData:
        return pa.RecordBatch.empty()


async def test(sim_init: Callable[[], Simulator]):
    sim = sim_init()
    await sim.setup_done()


class TestSim:
    def __init__(self, num: int):
        pass

    async def setup_done(self):
        pass

    async def set_data(self, time: Time, **measurements: pa.RecordBatch):
        pass

    async def trigger(self):
        pass

    async def get_data(self):
        pass


def test_sim_init() -> TestSim:
    return TestSim(0)


async def main():
    await test(test_sim_init)
