from __future__ import annotations

import asyncio
import heapq
from abc import ABC, abstractmethod
from asyncio import Future
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import polars as pl  # noqa: F401  # pyright: ignore[reportUnusedImport]
import pyarrow as pa
import pyarrow.compute as pac
from pandas._config.config import contextmanager

from mosaik.simulator import ModelMeta, SimMeta
from mosaik.tiered_time import TieredDuration, TieredTime

if TYPE_CHECKING:
    from mosaik.simulator import Attr, EventData, MeasData, ModelName, Simulator

type EventDataTable = dict[ModelName, dict[Attr, pa.Table]]


class MeasurementSource(ABC):
    @abstractmethod
    def get_data(self, time: TieredTime) -> pa.Array:
        """Get the data that this source provides (at the current time).

        The result should be an Arrow Array with as many rows as the
        receiving simulator has entities of the corresponding type.

        Sometimes, the consumer will source multiple sources for the
        data. In this case, each source still needs to provide a value
        for every entity of the consumer, but rows that are unused
        (because the actual value is provided by a different source) may
        be null, even if the resulting type is non-nullable.
        """


@dataclass
class SimulatorSource(MeasurementSource):
    sim: SimRunner[Simulator]
    model: ModelName
    attr: str
    take_mask: pa.Int64Array
    """For each row (=entity) of the destination simulator, which row of
    the source simulator provides the data.

    This can be used in the method
    :meth:`Array.take <pyarrow.Array.take>` to have the computation
    performed by Arrow.
    """

    def get_data(self, time: TieredTime) -> pa.Array:
        return self.sim._meas_out[self.model].column(self.attr).take(self.take_mask)


@dataclass
class ConstantSource(MeasurementSource):
    """Input measurements for a simulator set to a constant value.

    This is used if the scenario author sets the value of a measurement
    instead of connecting a simulator.
    """

    constant: pa.Array

    def get_data(self, time: TieredTime) -> pa.Array:
        return self.constant


@dataclass
class MeasurementAssembly:
    sources: Sequence[MeasurementSource]
    choice_mask: pa.Int64Array
    """For each row (=entity), the index in ``sources`` from which to
    take the value for this row.

    For example, if there are two sources, and ``choice_mask`` is
    [0, 1, 0], the first entity's input will come from source 0, the
    second entity's input will come from source 1, and the third will
    come from source 0 again.

    This can be used in :meth:`pyarrow.compute.choose` to have the
    calculation be done by Arrow.
    """


@dataclass
class EventPostage:
    """Data describing how to transform one simulator's event outputs
    into another simulator's event inputs.

    The :meth:`post` method perform the described transformtion.
    """

    postage: pa.Table
    num_adds: int
    num_drops: int
    dest_tiers: int

    def post(self, event_out: pa.Table) -> pa.Table:
        """Transform the event outputs ``event_out`` according to this
        specification.

        ``event_out`` should be an Arrow table with columns
        *out_time_0*, *out_time_1*, ... (depending on the number of time
        tiers for the source simulator), *out_eidx*, and *value*. The
        return value is a table with columns *in_time_0*, *in_time_1*,
        ... (time tiers of the destination simulator), *in_eidx*, and
        *value*.
        """
        result = self.postage.join(
            event_out, keys="out_eidx", right_keys="out_eidx", join_type="inner"
        )
        for tier in range(self.num_adds):
            result = result.add_column(
                tier,
                f"in_time_{tier}",
                pac.add(
                    result.column(f"out_time_{tier}"),
                    result.column(f"add_{tier}"),
                ),
            )
        drops = (
            [f"out_time_{tier}" for tier in range(self.num_drops)]
            + [f"add_{tier}" for tier in range(self.num_adds)]
            + ["out_eidx"]
        )
        result = result.drop_columns(drops)
        return result


class SimRunner[S: Simulator]:
    """This class tracks a mosaik simulator, called "this simulator" in
    this documentation.

    It stores the data and methods necessary to perform scheduling for
    this simulator.
    """

    _sim: S
    """This :class:`SimRunner`'s simulator."""
    _next_step: Future[TieredTime | None]
    _event_scheduled_steps: list[TieredTime]
    """Heap of future steps for this simulator based on incoming events.

    The simulator's potential self-scheduled step is tracked in
    :attr:`_self_scheduled_step`, instead.
    """
    _self_scheduled_step: TieredTime | None
    """A self-step scheduled by this simulator.

    While stepping, this will also store a non-self-scheduled step to
    prevent us from advancing other simulators too soon.

    This is separate from :attr:`_event_scheduled_steps` because the
    self step is reset after every step (even if that step occurred at a
    different time. This is useful because it allows event-based
    simulators to update their self step when new events come in before
    the previously scheduled self step. Often, by that time, they can
    tell that the self step will no longer be necessary at the
    originally scheduled time.
    """
    _providers: dict[SimRunner[Simulator], TieredTime]
    _consumers: list[tuple[SimRunner[Simulator], TieredDuration]]

    _event_in: EventDataTable
    """Input events set for this simulator's future by other simulators.
    """
    _meas_out: MeasData
    """Measurement output from this simulator's entities in the last
    simulated step.
    """

    _meas_assembly: dict[ModelName, dict[str, MeasurementAssembly]]
    """"Instructions" on how to assemble this simulator's measurement
    inputs.

    For each model, instructions on how to create its input RecordBatch
    by giving a :class:`MeasurementAssembly` for each column (=attr).
    """

    _event_postage: dict[
        ModelName,
        dict[Attr, tuple[EventPostage, SimRunner[Simulator], ModelName, Attr]],
    ]
    """"Instructions" on how to send data from this simulator's event
    output to other SimRunners.

    For each model and attribute, the :class:`EventPostage` (describing
    how to transform the data) and the receiving simulator, model, and
    attribute.
    """

    _last_step: TieredTime | None

    def __init__(self, sim: S):
        self._sim = sim
        self._meas_assembly = {}
        self._meas_out = {}  # [TODO] Get from sim or some form of "initial data"
        self._event_in = {
            model: {
                attr: pa.schema(
                    [
                        ("in_time_0", pa.int64()),
                        ("in_time_1", pa.int64()),
                        ("in_eidx", pa.int64()),
                        ("value", data_type),
                    ]
                ).empty_table()
                for attr, data_type in model_meta.in_events.items()
            }
            for model, model_meta in sim.meta.models.items()
        }
        self._next_step = Future()
        self._event_scheduled_steps = []
        self._self_scheduled_step = None

    async def run_until(self, end: TieredTime):
        """Run the simulator for all steps before ``end``.

        The simulator will not be automatically terminated at the end
        (so further calls with greater ``end`` times are possible); to
        do that call :meth:`finalize`.

        This coroutine must be scheduled together with the
        :meth:`run_until` coroutines of the other simulators in this
        simulation.
        """
        while (time := await self._next_step) is not None and time < end:
            # We set our self-step time to the current step time. This
            # prevents us from advancing other simulators too far if new
            # events come in while we're stepping.
            self._self_scheduled_step = time
            meas_in = self.assemble_meas_in()
            await self._sim.set_measurements(time, meas_in)

            has_event = False
            if has_event:
                event_in = self.assemble_event_in(time)
                next_self_step, event_out = await self._sim.trigger(time, event_in)
                self.propagate_event_out(event_out)
            else:
                next_self_step = None

            output_required = False
            if output_required:
                self._meas_out = await self._sim.get_data(time)

            with self.update_dependent_progress():
                self._self_scheduled_step = next_self_step
            self._last_step = time
            self._next_step = Future()

    def assemble_meas_in(self) -> dict[ModelName, pa.RecordBatch]:
        """Using the specification from :attr:`_meas_assembly`, create
        the input (measurement) data for this simulator as a dict
        mapping model names to record batches.
        """
        inputs: dict[ModelName, pa.RecordBatch] = {}
        for model, attr_assemblies in self._meas_assembly.items():
            inputs[model] = pa.RecordBatch.from_arrays(
                [
                    pac.choose(
                        assembly.choice_mask,
                        *(src.get_data() for src in assembly.sources),
                    )
                    for assembly in attr_assemblies.values()
                ],
                names=list(attr_assemblies.keys()),
            )
        return inputs

    def assemble_event_in(self, time: TieredTime) -> EventData:
        """Collect the event inputs relevant for the current step
        ``time``, i.e. those with a time stamp at or prior to ``time``.

        This also removes these events from the event tables.
        """
        # Abstract Expressions that can be used to filter record batches
        # down below.
        # [TODO] Figure out whether this is really the best way to do
        # this filtering according to lexicographic order. (Here, I
        # think having all the times in one column would help, but then,
        # I don't see how to write the tiered-duration addition in
        # EventPostage.post.)
        # [NOTE] Arrow's table joins somehow do not work with struct
        # columns! (This might also be a problem later, when the type of
        # value is supposed to be flexible and defined by the simulator
        # authors.)
        filter_expr: pac.Expression = True  # pyright: ignore[reportAssignmentType]
        for tier in range(len(time.tiers) - 1, -1, -1):
            t = time.tiers[tier]
            field = pac.field(f"in_time_{tier}")
            filter_expr = (field < t) | ((field == t) & filter_expr)
        event_in: EventData = {}
        for model, model_events in self._event_in.items():
            event_in[model] = {}
            for attr in model_events:
                event_in[model][attr] = (
                    model_events[attr]
                    .filter(filter_expr)
                    .combine_chunks()
                    .to_batches()[0]
                )
                model_events[attr] = model_events[attr].filter(~filter_expr)
        return event_in

    def propagate_event_out(self, event_out: EventData):
        for model, attrs in self._event_postage.items():
            for attr, (postage, dest_sim, dest_model, dest_attr) in attrs.items():
                dest_sim.add_events(
                    dest_model,
                    dest_attr,
                    postage.post(pa.Table.from_batches([event_out[model][attr]])),
                )

    def add_events(self, model: ModelName, attr: Attr, event_in: pa.Table):
        self._event_in[model][attr] = pa.concat_tables(
            [self._event_in[model][attr], event_in]
        )

        event_times: Iterable[TieredTime] = extract_event_times(event_in)
        with self.update_dependent_progress():
            for time in event_times:
                heapq.heappush(self._event_scheduled_steps, time)

    @contextmanager
    def update_dependent_progress(self):
        """Use this in a ``with`` block to track whether this
        simulator's next scheduled step changes and update dependent
        simulators if it does.

        Usage::
            with self.update_dependent_progress():
                # code that update this simulator's self step or events

        If the code results in a change of
        :attr:`earlist_scheduled_step`, dependent simulators are
        notified so that they can re-determine whether to step.
        """
        old_scheduled_step = self.earliest_scheduled_step
        yield
        new_scheduled_step = self.earliest_scheduled_step
        if new_scheduled_step != old_scheduled_step:
            assert new_scheduled_step is not None, (
                "adding to schedule cannot result in scheduled step changing to `None`"
            )
            for post_sim, delay in self._consumers:
                post_sim.shift_progress(self, new_scheduled_step + delay)

    def shift_progress(self, pre_sim: SimRunner[Simulator], time: TieredTime):
        """Update the earliest time at which ``pre_sim`` could trigger
        this simulator to ``time``. This will potentially cause this
        simulator to perform a step.
        """
        self._providers[pre_sim] = time
        self.check_for_step()

    def check_for_step(self):
        """Check whether the next step is fixed and resolve the
        :attr:`_next_step` future if so.

        Stepping is based on the properties
        :attr:`earliest_possible_step` (which is non-decreasing) and
        :attr:`earliest_scheduled_step` (which is non-increasing, except
        when this simulator actually steps). Once those two values
        agree, their value is the next step.
        """
        if (step := self.earliest_possible_step) == self.earliest_scheduled_step:
            self._next_step.set_result(step)

    @property
    def earliest_scheduled_step(self) -> TieredTime | None:
        if not self._event_scheduled_steps:
            return self._self_scheduled_step
        if not self._self_scheduled_step:
            return self._event_scheduled_steps[0]
        return min(self._self_scheduled_step, self._event_scheduled_steps[0])

    @property
    def earliest_possible_step(self) -> TieredTime | None:
        # [TODO] It would probably be better to have some form of heap
        # here that gets updated whenever new events come in.
        return min(self._providers.values(), default=None)


def extract_event_times(event_in: pa.Table) -> Iterable[TieredTime]:
    """From the tabel of in-events, extract the times at which they
    occur as :class:`TieredTime` objects.
    """
    # [TODO] Make number of time columns flexible
    # [TODO] Switch to native "unique" function if available instead of
    # using this `group_by` + `aggregate` trick.
    times = event_in.group_by(["in_time_0", "in_time_1"]).aggregate([])
    # [TODO] Iterating and turning into internal tiered times is clearly
    # terrible. Maybe we can store tiered times in these tables always?
    result = []
    for batch in times.to_batches():
        d = batch.to_pydict()
        for t0, t1 in zip(d["in_time_0"], d["in_time_1"]):
            result.append(TieredTime(t0, t1))
    return result


def make_record_batch(**array: list[Any] | pa.Array) -> pa.RecordBatch:
    """Helper to create record batches in a nicer way.

    Instead of a list of pa.Arrays, which usually have their types
    infered anyway, and a list of column names, this function takes
    the arrays as keyword arguments in the form of Python lists,
    converts them to pa.Array and uses the keyword as the column name.

    [NOTE] This is only intended for testing; in the actual core,
    Arrow's compute functions should be used.
    """
    return pa.record_batch(
        [arr if isinstance(arr, pa.Array) else pa.array(arr) for arr in array.values()],
        names=list(array.keys()),
    )


def make_table(*args, **kwargs) -> pa.Table:
    return pa.Table.from_batches([make_record_batch(*args, **kwargs)])


class HEMSSim:
    meta = SimMeta(
        models={"HEMS": ModelMeta(in_events={"P_set": pa.float64()})},
    )


TEST_EVENTS = make_table(
    in_time_0=[0, 0, 0, 3, 2, 7],
    in_time_1=[1, 10, 1, 0, 2, 8],
    in_eidx=[0, 1, 0, 0, 2, 0],
    value=[0.51, 11.2, 3.3, 54.0, 4.2, -7.0],
)


async def main():
    test_src_sim = SimRunner(HEMSSim())
    test_src_sim._meas_out = {
        "HEMS": make_record_batch(
            P_out=[100.0, 200.0],
        )
    }

    test_runner = SimRunner(HEMSSim())
    test_runner._meas_assembly = {
        "Load": {
            "P": MeasurementAssembly(
                sources=[
                    SimulatorSource(
                        sim=test_src_sim,
                        model="HEMS",
                        attr="P_out",
                        take_mask=pa.array([0, None, 0]),
                    ),
                    ConstantSource(pa.array([1.0, 2.0, 3.0])),
                    ConstantSource(pa.array([10.0, 20.0, 30.0])),
                ],
                choice_mask=pa.array([0, 1, 0]),
            )
        }
    }
    print(extract_event_times(TEST_EVENTS))
    test_runner.add_events(
        "HEMS",
        "P_set",
        TEST_EVENTS,
    )

    # print(pl.from_arrow(test_runner.assemble_meas_in()["Load"]))

    # print(test_runner._event_in["HEMS"]["P_set"], end="\n\n")
    print(test_runner.assemble_event_in(TieredTime(0, 1))["HEMS"]["P_set"], end="\n\n")
    # print(test_runner._event_in["HEMS"]["P_set"], end="\n\n")


if __name__ == "__main__":
    asyncio.run(main())
