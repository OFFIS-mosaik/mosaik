import sys

import pyarrow as pa
import pyarrow.compute as pac

old_in = pa.record_batch(
    [
        pa.array([1, 2, 3, 4, 5]),
        pa.array(["eins", "zwei", "drei", "vier", "fünf"]),
    ],
    names=["digits", "german"],
)

new0 = pa.record_batch([pa.array(["cinq", "trois"])], names=["french"])
take0 = pa.array([None, None, 1, None, 0])

new1 = pa.record_batch([pa.array(["one", "two", "three", "four"])], names=["english"])
take1 = pa.array([0, 1, 2, 3, None])

valids = pac.make_struct(pac.is_valid(take0), pac.is_valid(take1))
choices = pac.case_when(valids, 0, 1)

if __name__ == "__main__":
    print(valids)
    print(
        pac.add(
            pac.cast(pac.is_valid(take0), pa.int64()),
            pac.cast(pac.is_valid(take1), pa.int64()),
        )
    )

    sys.exit()
    print(pac.count(valids))
    print(old_in.to_pandas())
    print(new0.take(take0))
    print(new1.take(take1))
    print(
        pac.choose(
            choices,
            new0.column("french").take(take0),
            new1.column("english").take(take1),
        )
    )
