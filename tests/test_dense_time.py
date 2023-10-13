import hypothesis
import hypothesis.strategies as st
import networkx as nx

from mosaik.dense_time import DenseTime


def test_shortest_path_length_time_then_microstep():
	graph = nx.DiGraph()
	graph.add_edges_from([
		(0, 1, {"weight": DenseTime(1, 0)}),
		(1, 2, {"weight": DenseTime(0, 1)}),
		(0, 2, {"weight": DenseTime(2, 0)}),
	])
	distance = nx.shortest_path_length(graph, 0, 2, "weight")
	assert distance == DenseTime(1, 1)


def test_shortest_path_length_microstep_then_time():
	graph = nx.DiGraph()
	graph.add_edges_from([
		(0, 1, {"weight": DenseTime(0, 1)}),
		(1, 2, {"weight": DenseTime(1, 0)}),
		(0, 2, {"weight": DenseTime(2, 0)}),
	])
	distance = nx.shortest_path_length(graph, 0, 2, "weight")
	assert distance == DenseTime(1, 0)


dense_time = st.builds(DenseTime, st.integers(min_value=0), st.integers(min_value=0))


@hypothesis.given(dense_time, dense_time, dense_time)
def test_associative(d1, d2, d3):
	assert (d1 + d2) + d3 == d1 + (d2 + d3)
