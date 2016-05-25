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
`download <http://odysseus.informatik.uni-oldenburg.de/index.php?id=76&L=2>`_ Odysseus Server and Studio Client.

.. _mosaik_protocol_handler:

Connecting via mosaik protocol handler
======================================

The easiest way to connect to mosaik is to use the mosaik protocol handler in 
Odysseus, which is available as installable feature in Odysseus Studio. It uses 
the mosaik API through remote procedure calls (RPC) and offers a close coupling 
of mosaik and Odysseus. With this, a blocked simulation in mosaik or a blocked 
processing in Odysseus will block the other system as well. If this is a problem 
in your use case, you should look in the section :ref:`zero_mq`.

First we have to install the following `features 
<http://wiki.odysseus.informatik.uni-oldenburg.de/display/ODYSSEUS/How+to+install+new+features>`_ 
in odysseus:

* wrapper / mosaik
* server / key value processsing

After installing the features we create a new Odysseus project and in the 
project a new Odysseus script file. To use mosaik as source we can 
use the mosaik operator which contains a standard configuration of mandatory parameters.
The script-code in the Odysseus query language `PQL 
<http://odysseus.offis.uni-oldenburg.de:8090/display/ODYSSEUS/The+Odysseus+Procedural+Query+Language+%28PQL%29+Framework>`_ 
looks like this:

.. code-block:: sql
   
  #PARSER PQL
  #METADATA TimeInterval
  #QUERY
  mosaikCon = MOSAIK({SOURCE = 'mosaik', type='simapi'})

This is for the standard configuration. If you want to change something, for example
to use another port, you need a more detailed configuration:

.. code-block:: sql
   
  #PARSER PQL
  #METADATA TimeInterval
  #QUERY
  mosaikCon = ACCESS({TRANSPORT = 'TCPServer',
                      PROTOCOL = 'mosaik',
                      SOURCE = 'mosaik',
                      DATAHANDLER = 'KeyValueObject',
                      WRAPPER = 'GenericPush',
                      OPTIONS = [
                        ['port', '5554'],
                        ['byteorder', 'LITTLE_ENDIAN']
                      ]})

As we can see the protocol 'mosaik' is chosen. When the query is started, the mosaik 
protocol handler in Odysseus opens a TCP server for receiving data from mosaik.

Before we can receive data, we have to adapt our mosaik :doc:`scenario<../scenario-definition>`.
Here we take the mosaik-demo as an example. The Odysseus simulator is treated 
just like any other component in mosaik. It has to be added to the ``SIM_CONFIG`` parameter.
For the connection to the simulator the ``connect`` command is used and the IP 
address and port of Odysseus have to be specified:

.. code-block:: python

	SIM_CONFIG = {
	
	    ...
	    
	    'Odysseus': {
	        'connect': '127.0.0.1:5554'
	    }
	}

After that, we have to initialize the simulator and connect it to all components whose data we want to revceive in Odysseus.
For the mosaik-demo, we have to add the following lines of code to the scenario definition:

.. code-block:: python

  ... 
   
  # Start simulators
  odysseusModel = world.start('Odysseus', step_size=15*60)

  # Instantiate models
  odysseus = odysseusModel.Odysseus.create(1)

  # Connect entities to odysseus
  connect_many_to_one(world, nodes, odysseus[0], 'P', 'Vm')
  connect_many_to_one(world, houses, odysseus[0], 'P_out')
  connect_many_to_one(world, pvs, odysseus[0], 'P')
  
  ...

Now we have set up everything to receive mosaiks data in Odysseus.
To begin transfering data we have to start first the query in Odysseus and then the simulation in mosaik.

For more information on how to use Odysseus visit :doc:`part two <odysseus2>`.

.. _zero_mq:

Connecting via ZeroMQ
=====================

In contrast to the close coupling via mosaik protocol handler the coupling via 
`ZeroMQ <https://en.wikipedia.org/wiki/%C3%98MQ>`_ is more loose.
Mosaik sends all data as data stream with ZeroMQ and Odysseus can even be closed 
and restarted during the simulation without affecting mosaik.
This behaviour holds the risk of loosing data so it should only be used if this 
doesn't cause problems.

First we have to install the following `features <http://wiki.odysseus.informatik.uni-oldenburg.de/display/ODYSSEUS/How+to+install+new+features>`_
for Odysseus:

* wrapper / Zero MQ
* server / key value processsing
* wrapper / mosaik (only if you want to use the mosaik operator)

After installing the feature we create a new Odysseus project 
and in the project a new Odysseus script file.
The messages sent by mosaik are formatted in JSON format and sent via ZeroMQ. 
So we have to choose the corresponding ZeroMQ transport handler and JSON protocol handler:

.. code-block:: sql
   
  #PARSER PQL
  #METADATA TimeInterval
  #QUERY
  mosaikCon = ACCESS({TRANSPORT = 'ZeroMQ',
                      PROTOCOL = 'JSON',
                      SOURCE = 'mosaik',
                      DATAHANDLER = 'KeyValueObject',
                      WRAPPER = 'GenericPush',
                      OPTIONS = [
                        ['host', '127.0.0.1'],
                        ['readport', '5558'],
                        ['writeport', '5559'],
                        ['byteorder', 'LITTLE_ENDIAN']
                      ]})

If you use the standard configurtion you can use the short version (feature "wrapper / mosaik" has to be installed):

.. code-block:: sql
   
  #PARSER PQL
  #METADATA TimeInterval
  #QUERY  
  mosaikCon = MOSAIK({SOURCE = 'mosaik', type='zeromq'})

After setting up Odysseus we have to install the mosaik-zmq adapter in our mosaik virtualenv.
It can be downloaded from the mosaik wrapper folder in the odysseus SVN 
`repository <http://wiki.odysseus.informatik.uni-oldenburg.de/display/ODYSSEUS/Development+with+Odysseus>`_:

* User: lesend
* Password: rurome48
* URL: http://isdb1.offis.uni-oldenburg.de/repos/odysseus/trunk/wrapper/mosaik/mosaik-zmq-simulator/

To install it we have to activate our mosaik virtualenv and execute:

.. code-block:: python

  pip install *path*/mosaik-zmq-0.1.tar.gz

The mosaik-zmq adapter is treated in mosaik like any other component of the simulation.
If we use the mosaik demo for an example we have to add the new simulator to 
the ``SIM_CONFIG`` parameter:

.. code-block:: python

  SIM_CONFIG = {
  
      ...
      
      'ZMQ': {
          'cmd': 'mosaik-zmq %(addr)s'
      } 
  }

Also we have to initialize the ZeroMQ simulator and connect it to other components:

.. code-block:: python

  ...
  
  # Start simulators
  zmqModel = world.start'ZMQ', step_size=15*60, duration=END)

  # Instantiate models
  zmq = zmqModel.Socket(host='tcp://*:', port=5558, socket_type='PUB')

  # Connect entities to zeromq
  connect_many_to_one(world, nodes, zmq, 'P', 'Vm')
  connect_many_to_one(world, houses, zmq, 'P_out')
  connect_many_to_one(world, pvs, zmq, 'P')
  
  ...

For more information on how to use Odysseus visit :doc:`part two <odysseus2>`.
