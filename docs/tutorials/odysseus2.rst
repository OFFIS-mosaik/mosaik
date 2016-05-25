==============================================================
Using Odysseus to process, visualize and store simulation data
==============================================================

This tutorial will give some examples on how you can use Odysseus to process, 
visualize and store the data from mosaik. More information about connecting 
mosaik and Odysseus can be found in the :doc:`first part <odysseus>` of the 
tutorial and more about Odysseus in general can be found in its 
`documentation <http://wiki.odysseus.informatik.uni-oldenburg.de/display/ODYSSEUS>`_.
If you have no experience with Odysseus you should first visit the tutorials in 
its documentation. `Simple query processing <http://wiki.odysseus.informatik.uni-oldenburg.de/display/ODYSSEUS/Simple+Query+Processing>`_ 
and `selection, projection and map <http://wiki.odysseus.informatik.uni-oldenburg.de/display/ODYSSEUS/Selection%2C+Projection+and+Map>`_ 
should explain the basics.

.. _processing:

Processing
==========

Mosaik sends data in JSON format and so the key-value-object has to be used as datatype for receiving in Odysseus.
But most operators in Odysseus are based on relational tuples with a fixed schema,
so it can be useful to transform arriving key-value objects to relational tuples.
For this the `keyvaluetotuple <http://wiki.odysseus.informatik.uni-oldenburg.de/display/ODYSSEUS/KeyValueToTuple+operator>`_ operator can be used.
It creates relational tuples with the given attributes and omitts all data, which is not included in the schema:

.. code-block:: sql

	tuples = KEYVALUETOTUPLE({
		SCHEMA = [
			['odysseus_0.Vm.PyPower-0.0-tr_sec', 'Double'],
			['odysseus_0.Vm.PyPower-0.0-node1', 'Double'],
			['odysseus_0.Vm.PyPower-0.0-node2', 'Double'],
			['odysseus_0.Vm.PyPower-0.0-node3', 'Double'],
			['odysseus_0.Vm.PyPower-0.0-node4', 'Double'],
			['timestamp', 'STARTTIMESTAMP']
		], 
		KEEPINPUT = false, 
		TYPE = 'mosaik'}, 
		mosaikCon)

For better handling we can rename the attributes with the `rename <http://wiki.odysseus.informatik.uni-oldenburg.de/display/ODYSSEUS/Rename+operator>`_ operator:

.. code-block:: sql

	renamedTuples = RENAME({aliases = 
			['tr_sec_Vm', 'node1_Vm', 'node2_Vm', 'node3_Vm', 'node4_Vm', 'timestamp']
		}, tuples)

We can also add computations to the data with a `map <http://wiki.odysseus.informatik.uni-oldenburg.de/display/ODYSSEUS/Map+operator>`_ operator. 
The expressions parameter contains first the computation and second the new name for every attribute.
In this example the deviation of voltage to the nominal voltage of 230 V is calculated (more information about the offered functions can be found `here <http://wiki.odysseus.informatik.uni-oldenburg.de/display/ODYSSEUS/Functions+and+Operators>`_):

.. code-block:: sql

	voltageDeviation = MAP({EXPRESSIONS = [
			['abs(230 - tr_sec_Vm)', 'dev_tr_sec_Vm'],
			['abs(230 - Node1_Vm)', 'dev_Node1_Vm'],
			['abs(230 - Node2_Vm)', 'dev_Node2_Vm'],
			['abs(230 - Node3_Vm)', 'dev_Node3_Vm'],
			['abs(230 - Node4_Vm)', 'dev_Node4_Vm']
		]}, renamedTuples)

By using the `aggregate <http://wiki.odysseus.informatik.uni-oldenburg.de/display/ODYSSEUS/Aggregate+%28and+Group%29+operator>`_ 
operator we are able to calculate e.g. the average values.
We have to add an `timewindow <http://wiki.odysseus.informatik.uni-oldenburg.de/display/ODYSSEUS/TimeWindow>`_ 
operator first to have the right timestamps for aggregating.

.. code-block:: sql

	windowedTuples = TIMEWINDOW({SIZE = [5, 'MINUTES']}, voltageDeviation)
	aggregatedTuples = AGGREGATE({
		AGGREGATIONS = [
			['AVG', 'dev_tr_sec_Vm', 'AVG_dev_tr_sec_P'],
			['AVG', 'dev_Node1_Vm', 'AVG_dev_Node1_P'],
			['AVG', 'dev_Node2_Vm', 'AVG_dev_Node2_P'],
			['AVG', 'dev_Node3_Vm', 'AVG_dev_Node3_P'],
			['AVG', 'dev_Node4_Vm', 'AVG_dev_Node4_P']
			]}, 
		windowedTuples)

.. _visualisation:

Visualisation
=============

To visualize data in Odysseus dashboards can be used, which can contain different graphs.
For the data stream shown in the section above an exemplary dashboard could look like the following picture:

.. image:: /_static/odysseus_visualisation.*
    :width: 600
    :align: center
    :alt: visualisation of simulation data in Odysseus

More information about dashboards in Odysseus can be found in the `documentation <http://wiki.odysseus.informatik.uni-oldenburg.de/display/ODYSSEUS/Dashboard+Feature>`_.

.. _storing:

Storing
==========

If we want to save the results of our Odysseus query, we can use the `sender <http://wiki.odysseus.informatik.uni-oldenburg.de/display/ODYSSEUS/Sender+operator>`_ operator to export it, e.g. to a csv file:

.. code-block:: sql

	send = SENDER({
		SINK='writeCSV',
		transport='File',
		wrapper='GenericPush',
		protocol='CSV',
		dataHandler='Tuple',
		options=[
			['filename','${WORKSPACEPROJECT}\output2.csv'],
			['csv.writeMetadata', 'true']
		]}, aggregatedTuples)

Odysseus also offers adapters to store the processed data to different databases (e.g. mysql, postgres and oracle). 
More details can be found `here <http://wiki.odysseus.informatik.uni-oldenburg.de/display/ODYSSEUS/Database+Feature>`_.
