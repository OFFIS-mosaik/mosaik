from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import pyarrow as pa
import pyarrow.compute as pac

from mosaik.simulator import ModelMeta, SimMeta
from mosaik.tiered_time import TieredTime

if TYPE_CHECKING:
    from mosaik.simulator import Attr, EventData, MeasData, ModelName, Simulator, Time

type EventDataTable = dict[ModelName, dict[Attr, pa.Table]]


class MeasurementSource(ABC):
    @abstractmethod
    def get_data(self) -> pa.Array:
        """Get the data that this source provides (at the current time).

        The result should be an Arrow Array with as many rows as the
        receiving simulator has entities of the corresponding type.
        (Values may be null if unused.)
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

    def get_data(self) -> pa.Array:
        return self.sim._meas_out[self.model].column(self.attr).take(self.take_mask)


@dataclass
class ConstantSource(MeasurementSource):
    """Input measurements for a simulator set to a constant value.

    This is used if the scenario author sets the value of a measurement
    instead of connecting a simulator.
    """

    constant: pa.Array

    def get_data(self) -> pa.Array:
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
    _sim: S
    _next_event_time: Time | None = None

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
    """

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

    async def run_until(self, end: Time):
        """Run the simulator for all steps before ``end``.

        The simulator will not be automatically terminated at the end
        (so further calls with greater ``end`` times are possible); to
        do that call :meth:`finalize`.

        This coroutine must be scheduled together with the
        :meth:`run_until` coroutines of the other simulators in this
        simulation.
        """
        while (time := await self.get_next_step()) < end:
            meas_in = self.assemble_meas_in()
            await self._sim.set_measurements(time, meas_in)

            has_event = False
            if has_event:
                event_in = self.assemble_event_in(time)
                _self_step, event_out = await self._sim.trigger(time, event_in)
                self.propage_event_out(event_out)

            output_required = False
            if output_required:
                self._meas_out = await self._sim.get_data(time)

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
        # Abstract Expressions that can be used to filter record batches
        # down below.
        # [TODO] Figure out whether this is really the best way to do
        # this filtering according to lexicographic order. (Here, I
        # think having all the times in one column would help, but then,
        # I don't see how to write the tiered-duration addition in
        # EventPostage.post.)
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

    async def get_next_step(self) -> Time:
        """The next step happens when an event is scheduled or this
        simulator's outputs are required.
        """
        return 0


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


if __name__ == "__main__":
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
    test_runner.add_events(
        "HEMS",
        "P_set",
        make_table(
            in_time_0=[0, 0, 3, 2, 7],
            in_time_1=[1, 10, 0, 2, 8],
            in_eidx=[0, 1, 0, 0, 0],
            value=[0.51, 11.2, 3.3, 4.2, -7.0],
        ),
    )
    # print(pl.from_arrow(test_runner.assemble_meas_in()["Load"]))

    # print(test_runner._event_in["HEMS"]["P_set"], end="\n\n")
    print(test_runner.assemble_event_in(TieredTime(0, 1))["HEMS"]["P_set"], end="\n\n")
    # print(test_runner._event_in["HEMS"]["P_set"], end="\n\n")
