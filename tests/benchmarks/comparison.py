import networkx as nx
import sys


def write_exeuction_graph(world, scenario_file_name):
	nx.write_gexf(world.execution_graph, scenario_file_name.replace('.py', '.gexf'))


def compare_execution_graph(world, scenario_file_name):
	eg = nx.read_gexf(scenario_file_name.replace('.py', '.gexf'))

	# The execution graph contains data about the execution time, which will be removed here for comparison
	nodes = list(world.execution_graph.nodes(data=True))
	for node in nodes:
		if 't' in node[1]:
			node[1].pop('t')
		if 't_end' in node[1]:
			node[1].pop('t_end')

	eg_nodes = list(world.execution_graph.nodes(data=True))
	for eg_node in eg_nodes:
		if 't' in eg_node[1]:
			eg_node[1].pop('t')
		if 't_end' in eg_node[1]:
			eg_node[1].pop('t_end')


	equal_nodes = nx.utils.nodes_equal(world.execution_graph, eg)
	equal_edges = nx.utils.edges_equal(world.execution_graph, eg)

	# graphs_equal is somehow always returning False
	# graph1.adj == graph2.adj and graph1.graph == graph2.graph is usually True, but
	# graph1.nodes == graph2.nodes not
	# https://networkx.org/documentation/stable/_modules/networkx/utils/misc.html#graphs_equal

	# During saving the graph to file some elements are added, which will be removed here
	#for item in eg.adj:
	#	for item2 in eg.adj[item]:
	#		if 'id' in eg.adj[item][item2]:
	#			eg.adj[item][item2].pop('id')

	#for graph_item in list(eg.graph):
	#	eg.graph.pop(graph_item)

	#equal = nx.utils.graphs_equal(world.execution_graph, eg)
	#print('')
	#print('-----')
	#print(world.execution_graph.nodes)
	#print(type(world.execution_graph.nodes))
	#print('-----')
	#print(eg.nodes)
	#print(type(eg.nodes))
	#print(world.execution_graph.nodes == eg.nodes)

	#for i in range(len(eg.nodes)):
	#	print(list(world.execution_graph.nodes)[i])
	#	print(list(eg.nodes)[i])
	#	print(list(world.execution_graph.nodes)[i] == list(eg.nodes)[i])

	if not (equal_nodes and equal_edges):
		sys.exit(3)
