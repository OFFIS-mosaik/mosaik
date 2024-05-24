from __future__ import annotations

import hypothesis
import hypothesis.strategies as st

from mosaik.tiered_time import TieredInterval, TieredTime


def tiered_intervals(pre_length: int, length: int):
    """Strategy to build TieredInterval objects with the given
    pre_length and length.
    """
    return st.builds(
        lambda tiers, cutoff: TieredInterval(*tiers, cutoff=cutoff, pre_length=pre_length),
        st.tuples(*((st.integers(min_value=0),) * length)),
        st.integers(min_value=1, max_value=min(pre_length, length)),
    )


def asso_triples(min_length: int = 1, max_length: int = 7):
    """Strategy to build a triple of TieredIntervals such that their
    lengths and pre_lengths line up for addition. Each (pre_)length will
    be constrained between the given min_length and max_length.
    """
    lengths = st.integers(min_length, max_length)
    return st.tuples(lengths, lengths, lengths, lengths).flatmap(
        lambda lengths: st.tuples(
            tiered_intervals(lengths[0], lengths[1]),
            tiered_intervals(lengths[1], lengths[2]),
            tiered_intervals(lengths[2], lengths[3]),
        )
    )


@hypothesis.given(asso_triples(1, 10))
def test_associative(
    asso_triple: tuple[TieredInterval, TieredInterval, TieredInterval]
):
    """Test that TieredInterval addition is associative."""
    ti1, ti2, ti3 = asso_triple
    assert (ti1 + ti2) + ti3 == ti1 + (ti2 + ti3)


def tiered_times(length: int):
    return st.builds(
        lambda tiers: TieredTime(*tiers),
        st.tuples(*((st.integers(0),) * length))
    )


def torsor_triples(min_length: int = 1, max_length: int = 7):
    """Strategy to build a triple of TieredIntervals such that their
    lengths and pre_lengths line up for addition. Each (pre_)length will
    be constrained between the given min_length and max_length.
    """
    lengths = st.integers(min_length, max_length)
    return st.tuples(lengths, lengths, lengths).flatmap(
        lambda lengths: st.tuples(
            tiered_times(lengths[0]),
            tiered_intervals(lengths[0], lengths[1]),
            tiered_intervals(lengths[1], lengths[2]),
        )
    )


@hypothesis.given(torsor_triples(1, 10))
def test_torsor(
    torsor_triple: tuple[TieredTime, TieredInterval, TieredInterval]
):
    tt, ti1, ti2 = torsor_triple
    assert (tt + ti1) + ti2 == tt + (ti1 + ti2)
