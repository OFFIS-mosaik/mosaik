=============
Odysseus
=============
         
`Odysseus <http://odysseus.informatik.uni-oldenburg.de/index.php?id=1&L=2>`_ is 
a framework for in-memory data stream management that is designed for 
online processing of big data. Large volumes of data such as continuously 
occurring events or sensor data can be processed in real time. In combination 
with mosaik Odysseus can be used to process, visualise and store the results of 
mosaik during a simulation.

Process data
============

Odysseus allows to process data streams with different operators.
For instance, the operators SELECT and PROJECT can be used to filter the data, 
aggregations for specific periods of time can be calculated and key-value data 
can be transformed in relational data and the other way round.
Multiple operators are connected with each other, to form so-called operator-graphs.
An example of such a graph is shown below:

.. image:: /_static/odysseus_queryplan.*
    :width: 125px
    :align: center
    :alt: using operators in Odysseus

The query for this graph can be found in the :doc:`tutorial </tutorial/odysseus2/>`.

Visualise data
==============

All data can be visualised in lists, tables or graphs.
For more complex visualisation, dashboards can be created and individually customised:

.. image:: /_static/odysseus_dashboard.*
    :width: 500px
    :align: center
    :alt: visualisation of an mosaik simulation with Odysseus

Store data
==========

Odysseus also offers connectors to transform data to different formats and databases,
which makes it suitable to store simulation data.

Further information about how to install Odysseus and how to use it with mosaik 
can be found in the :doc:`tutorial </tutorial/odysseus/>`.
