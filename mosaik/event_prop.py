from typing import Any

import polars as pl
import pyarrow as pa
import pyarrow.compute as pac

from .simrunner import EventPostage, make_record_batch


def make_union(types: list[int], **values: list[Any]) -> pa.UnionArray:
    return pa.UnionArray.from_sparse(
        pa.array(types, type=pa.int8()),
        [pa.array(value) for value in values.values()],
        field_names=list(values.keys()),
    )


def make_table(*args, **kwargs) -> pa.Table:
    return pa.Table.from_batches([make_record_batch(*args, **kwargs)])


def example_with_union():
    # This might be to impractical, as the support for working with
    # these union types in Arrow is not great.
    events = make_record_batch(
        time=[1, 2, 2, 1, 3],
        out_eidx=[0, 0, 1, 1, 0],
        value=make_union(
            [0, 0, 0, 1, 1],
            str=["foo", "bar", None, "test", None],
            int=[None, None, None, 42, 36],
        ),
    )
    f = pac.is_valid(pac.struct_field(pac.field("value"), 0))
    print(pac.struct_field(events.column("value"), 0))
    print(events.filter(f))


def example_without_union():
    events = make_table(
        out_time_0=[1, 2, 2, 1, 3],
        out_time_1=[3, 1, 2, 3, 2],
        out_eidx=[0, 0, 1, 2, 0],
        value=["foo", "bar", "baz", "fib", "doh"],
    )
    print(pl.from_arrow(events))
    postage = EventPostage(
        make_table(
            add_0=[0, 2, 1],
            in_time_1=[1, 1, 1],
            in_time_2=[4, 2, 3],
            out_eidx=[0, 0, 1],
            in_eidx=[1, 0, 0],
        ),
        num_adds=1,
        num_drops=2,
    )
    print(pl.from_arrow(postage.post(events)))


if __name__ == "__main__":
    example_without_union()
