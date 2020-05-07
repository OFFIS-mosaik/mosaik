==============================
Connecting mosaik and Odysseus
==============================

In this first part of the tutorial we cover the two ways to connect mosaik and 
:doc:`Odysseus<../ecosystem/odysseus>`, the :doc:`second part<odysseus2>` is about how 
to use Odysseus to process, visualize and store simulation data.

You can choose between two different solutions to connect mosaik and Odysseus.
Both have their advantages and disadvantages and therefore, the right choice depends on your use case.
We recommend to use the SimAPI version for beginners.

No matter which connection we use, we first have to 
`download <hhttp://odysseus.informatik.uni-oldenburg.de/downloads>`_ Odysseus Server and Studio Client.
For the first start of Odysseus Studio the default user "System" and password "manager" have to be used, 
the tenant can be left empty.

.. _mosaik_protocol_handler:

Connecting via mosaik protocol handler
======================================

The easiest way to connect to mosaik is to use the mosaik protocol handler in 
Odysseus, which is available as installable feature in Odysseus Studio. It uses 
the mosaik API through remote procedure calls (RPC) and offers a close coupling 
of mosaik and Odysseus. With this, a blocked simulation in mosaik or a blocked 
processing in Odysseus will block the other system as well. If this is a problem 
in your use case, you should look in the section :ref:`zero_mq`.

First we have to install the mosaik `feature 
<http://wiki.odysseus.informatik.uni-oldenburg.de/display/ODYSSEUS/How+to+install+new+features>`_ 
from the incubcation site in odysseus, which can be found in the Odysseus Wrapper Plugins.

After installing the feature we create a new Odysseus project and in the 
project a new Odysseus script file (more information on Odysseus projects and script files can be found in this 
`tutorial <http://wiki.odysseus.informatik.uni-oldenburg.de/display/ODYSSEUS/Simple+Query+Processing>`_). 
To use mosaik as source we can 
use the mosaik operator which contains a standard configuration of mandatory parameters.
The script-code in the Odysseus query language `PQL 
<http://wiki.odysseus.informatik.uni-oldenburg.de/pages/viewpage.action?pageId=4587829>`_ 
looks like this:

.. literalinclude:: code/odysseus_tutorial_sources.qry
   :lines: 1-4

This is for the standard configuration. If you want to change something, for example
to use another port, you need a more detailed configuration:

.. literalinclude:: code/odysseus_tutorial_sources.qry
   :lines: 1-3,6-15

As we can see the protocol 'mosaik' is chosen. When the query is started, the mosaik 
protocol handler in Odysseus opens a TCP server for receiving data from mosaik.

Before we can receive data, we have to adapt our mosaik :doc:`scenario<../scenario-definition>`.
Here we take the mosaik-demo as an example. The Odysseus simulator is treated 
just like any other component in mosaik. It has to be added to the ``SIM_CONFIG`` parameter.
For the connection to the simulator the ``connect`` command is used and the IP 
address and port of Odysseus have to be specified:

.. literalinclude:: code/odysseus_mosaik_scenario.py
   :lines: 9,25-27

After that, we have to initialize the simulator and connect it to all components whose data we want to revceive in Odysseus.
For the mosaik-demo, we have to add the following lines of code to the scenario definition:

.. literalinclude:: code/odysseus_mosaik_scenario.py
   :lines: 47,51,53,54,60-61,63-64,79-81

Now we have set up everything to receive mosaiks data in Odysseus.
To begin transfering data we have to start first the query in Odysseus and then the simulation in mosaik.

For more information on how to use Odysseus visit :doc:`part two <odysseus2>`.

.. _zero_mq:

Connecting via ZeroMQ
=====================

In contrast to the close coupling via mosaik protocol handler the coupling via 
`ZeroMQ <https://zeromq.org/>`_ is more loose.
Mosaik sends all data as data stream with ZeroMQ and Odysseus can even be closed 
and restarted during the simulation without affecting mosaik.
This behaviour holds the risk of loosing data so it should only be used if this 
doesn't cause problems.

First we have to install the following `features <http://wiki.odysseus.informatik.uni-oldenburg.de/display/ODYSSEUS/How+to+install+new+features>`_
for Odysseus from incubation site:

* Odysseus Wrapper Plugins / Zero MQ
* Odysseus Wrapper Plugins / mosaik (only if you want to use the mosaik operator)

And from the update site:

* Odysseus Odysseus_core Plugins / Json Wrapper

After installing the features we create a new Odysseus project 
and in the project a new Odysseus script file.
The messages sent by mosaik are formatted in JSON format and sent via ZeroMQ. 
So we have to choose the corresponding ZeroMQ transport handler and JSON protocol handler:

.. literalinclude:: code/odysseus_tutorial_sources.qry
   :lines: 1-2,18-29

If you use the standard configurtion you can use the short version (feature "wrapper / mosaik" has to be installed):

.. literalinclude:: code/odysseus_tutorial_sources.qry
   :lines: 1-3,17

After setting up Odysseus we have to install the mosaik-zmq adapter in our mosaik virtualenv.
It is available on `GitLab <https://gitlab.com/mosaik/mosaik-zmq>`_ and PyPI.
To install it we have to activate our mosaik virtualenv and execute (if there are errors during installation have a look in the 
`readme <https://gitlab.com/mosaik/mosaik-zmq>`_):

.. code-block:: python

  pip install mosaik-zmq

The mosaik-zmq adapter is treated in mosaik like any other component of the simulation.
If we use the mosaik demo, we have to add the new simulator to 
the ``SIM_CONFIG`` parameter:

.. literalinclude:: code/odysseus_mosaik_scenario.py
   :lines: 9,13-15

Also we have to initialize the ZeroMQ simulator and connect it to other components:

.. literalinclude:: code/odysseus_mosaik_scenario.py
   :lines: 47,52-54,62-64,83-85

For more information on how to use Odysseus visit :doc:`part two <odysseus2>`.
