import networkx as nx
import sys

def remove_time_stamps(graph):
	"""
	The execution graph contains data about the execution time, which will be removed here for comparison.

	@param graph: the graph to remove timestamps
	"""
	nodes = list(graph.nodes(data=True))
	for node in nodes:
		if 't' in node[1]:
			node[1].pop('t')
		if 't_end' in node[1]:
			node[1].pop('t_end')


def remove_ids_and_labels(graph):
	"""
	During saving the graph to file some elements are added, which will be removed here.

	@param graph: the graph to remove ids and labels
	"""
	for item in graph.adj:
		for item2 in graph.adj[item]:
			if 'id' in graph.adj[item][item2]:
				graph.adj[item][item2].pop('id')

	nodes = list(graph.nodes(data=True))
	for node in nodes:
		if 'label' in node[1]:
			node[1].pop('label')


def fix_inputs(graph):
	"""
	The inputs dictionary is stored as string and has to be converted to dict again.

	@param graph: the graph to be fixed
	"""
	nodes = list(graph.nodes(data=True))
	for node in nodes:
		if 'inputs' in node[1]:
			node[1]['inputs'] = eval(node[1]['inputs'])


def write_exeuction_graph(world, scenario_file_name):
	"""
	Write the execution_graph of a world to file for later comparison.

	@param world: the containing execution_graph of this world will be written to file
	@param scenario_file_name: file name for storing the execution graph.
	"""
	remove_time_stamps(world.execution_graph)
	nx.write_gexf(world.execution_graph, scenario_file_name.replace('.py', '.gexf'))


def compare_execution_graph(world, scenario_file_name):
	"""
	Compares the execution graph from a file and the provided world to check if the simulation resulted in the
	expected results.

	@param world: world object with the execution graph written (debug=True) to compare
	@param scenario_file_name: file name to the old execution graph to compare the simulation results with
	"""
	remove_time_stamps(world.execution_graph)

	# read in previously written execution graph for comparision
	eg = nx.read_gexf(scenario_file_name.replace('.py', '.gexf'))
	remove_ids_and_labels(eg)
	fix_inputs(eg)

	equal_nodes = nx.utils.nodes_equal(world.execution_graph.nodes(data=True), eg.nodes(data=True))
	equal_edges = nx.utils.edges_equal(world.execution_graph.edges(data=True), eg.edges(data=True))
	equal_adj = world.execution_graph.adj == eg.adj

	if not (equal_nodes and equal_edges and equal_adj):
		sys.exit(3)
