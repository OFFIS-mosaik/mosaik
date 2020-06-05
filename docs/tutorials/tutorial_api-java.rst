.. _tutorial_api-java:

========================================================
Integrating a Model in Java
========================================================

What do we do if we want to connect a simulator to mosaik which ist  written in Java? In this tutorial
we will describe how to create a simple model in Java and integrate it into mosaik using the
mosaik-Java :doc:`high level API</mosaik-api/index>`. We will
do this with the help of our simple model from the Python tutorial, 
i. e. we will try to replicate the first part of the :doc:`Python tutorial</tutorials/examplesim>` as close as possible.

Getting the Java API
====================

First you have to get the sources of the `mosaik-API for Java <https://gitlab.com/mosaik/mosaik-api-java>`_ 
which is provided on Gitlab. Clone it and put it in the development environment of your choice.

Creating the model
==================

Next we create a Java class for our model.  Our example model has exact the same behaviour 
as our simple :ref:`model <the_simulator>` in the Python tutorial. To distinguish it
from the Python-model we call it *JModel*. The only difference to the Python-model
is that in Java we need two constructors (with and without init value) and getter 
and setter methods to access the variables *val* and *delta*.

.. literalinclude:: code/src/de/offis/mosaik/api/JExampleSim.java
   :language: java 
   :lines: 177-205

Creating the simulator
======================

A simulator provides the functionality that is necessary to manages instances of our model and to
execute the models. We need a method *addModel* to create instances of our model and an ArrayList 
*models* to store them. The *step* method executes a simulation for each model instance. To access 
the *values* and *deltas* we need getter and setter methods.  In our example the class 
implementing these functionalities is called JSimulator.

.. literalinclude:: code/src/de/offis/mosaik/api/JExampleSim.java
   :language: java 
   :lines: 136-175

Implementing the mosaik API
===========================

Finally we need to implement the mosaik-API methods. In our example this is
done in a class called JExampleSim. This class has to extent the abstract class
*Simulator* from mosaik-java-api which is the Java-equivalent to the 
:ref:`Simulator class <simulator_class>` in Python. The class *Simulator* provides 
the four mosaik-API-calls ``init()``, ``create()``, ``step()``, and ``getData()``
which we have to implement. For a more detailed explanation of the API-calls see the 
:ref:`API-documentation <api-calls>`.

But first we have to put together the :ref:`meta-data <meta_data>` containing information 
about models, attributes, and parameters of our simulator. 'models' are all models our simulator
provides. In our case this is only *JModel*. 'public': true tells mosaik that it is allowed to
create models of this class. 'params' are parameter that are passed during initialisation, in our
case this is *init_val*. 'attrs' is a list of values that can be exchanged.

.. literalinclude:: code/src/de/offis/mosaik/api/JExampleSim.java
   :language: java 
   :lines: 21-30

First method is **init()** that returns the 
meta data. In addition it is possible to pass arguments for initialization. In our
case there is *eid_prefix* which will be used to name instances of the models:

.. literalinclude:: code/src/de/offis/mosaik/api/JExampleSim.java
   :language: java 
   :lines: 40-46

**create()** creates new instances of the model *JModel* by calling the *add_model*-method of 
*JSimulator*. It also assigns ID (eid) to the models, so that it is able to keep
track of them. It has to return a list with the name (eid) and type of the models. You can find
more details about the return object in the :ref:`API-documentation <api.create>`.

.. literalinclude:: code/src/de/offis/mosaik/api/JExampleSim.java
   :language: java 
   :lines: 48-67

**step()** tells the simulator to perform a simulation step. It passes the *time*, the current
simulation time, and *inputs*, a JSON data object with input data from preceding simulators. The 
structure of *inputs* is explained in the :ref:`API-documentation <api.step>`. If there are
new *delta*-values in *inputs* they are set in the appropriate model instance. Finally it 
calls the simulator's *step()*-method which, on its part, calls the *step()*-methods 
of the individual model-instances.


.. literalinclude:: code/src/de/offis/mosaik/api/JExampleSim.java
   :language: java 
   :lines: 71-99

**getData()** gets the simulator's output data from the last simulation step. It
passes *outputs*, a JSON data object that describes which parameters are requested. 
*getData()* goes through *outputs*, retrieves the requested values from the appropriate 
instances of JModel and puts it in *data*. The structure of *outputs* and *data* is 
explained in the :ref:`API-documentation <api.get_data>`.

.. literalinclude:: code/src/de/offis/mosaik/api/JExampleSim.java
   :language: java 
   :lines: 101-123

Connecting the simulator to mosaik
==================================

We use the same scenario as in our Python example :ref:`demo1 <demo1>`. 
The only thing we have to change is the way we connect our simulator to mosaik. 
There are two ways to do this:

- **cmd:** mosaik calls the Java API by executing the command given in *cmd*. Mosaik starts the
  Java-API in a new process and connects it to mosaik. This works only if your simulator 
  runs on the same machine as mosaik.

- **connect:** mosaik connects to the Java-API which runs as a TCP server. This works also 
  if mosaik and the simulator are running on different machines.

For more details about how to connect simulators to mosaik see the section about the 
:doc:`Sim Manager </simmanager>` in the mosaik-documentation.

.. _java_cmd:

Connecting the simulator using *cmd*
------------------------------------

We have to give mosaik the command how to start our Java simulator. This is done in 
:ref:`SIM_CONFIG <sim_config>`. The marked lines show the differences to our Python simulator.

.. code-block:: python
    :emphasize-lines: 3 - 4

    # Sim config. and other parameters
    SIM_CONFIG = {
        'JExampleSim': {
            'cmd': 'java -cp JExampleSim.jar de.offis.mosaik.api.JExampleSim %(addr)s',
        },
        'Collector': {
            'cmd': 'python collector.py %(addr)s',
        },
    }
    END = 10 * 60  # 10 minutes

The placeholder *%(addr)s* is later replaced  with IP address and port by mosaik. If we now 
execute demo_1.py we get the same :ref:`output <demo1_output>` as in our Python-example.

.. note::
	The command how to start the Java simulator may differ depending on your operating system. 
	If the command is complex, e. g. if it contains several libraries, it is usually better 
	to put it in a script and than call the script in *cmd*.


Connecting the simulator using *connect*
----------------------------------------

In this case the Java API acts as TCP server and listens at the given address 
and port. Let's say the simulator runs on a computer with the IP-address 1.2.3.4. 
We can now choose a port that is not assigned by `default <https://en.wikipedia.org/wiki/List_of_TCP_and_UDP_port_numbers>`_. 
In our example we choose port 5678. Make sure that IP-address and port is accessible from 
the computer that hosts mosaik (firewalls etc.).
  
.. note::
    Of course you can run mosaik and your simulator on the same machine by using
    ``127.0.0.1:5678`` (localhost). You may want to do this for testing and experimenting.
    Apart from that the connection with cmd (:ref:`see above <java_cmd>`) is usually 
    the better alternative because you don't have to start the Java part separately.

We have to tell mosaik how to connect to the simulator. This is done in :ref:`SIM_CONFIG <sim_config>`
in our scenario (demo1):

.. code-block:: python
    :emphasize-lines: 3 - 4

    # Sim config. and other parameters
    SIM_CONFIG = {
        'JExampleSim': {
            'connect': '1.2.3.4:5678',
        },
        'Collector': {
            'cmd': 'python collector.py %(addr)s',
        },
    }
    END = 10 * 60  # 10 minutes

The marked lines show the differences to our Python simulator. Our simulator is now called *JExampleSim*
and we need to give the simulator's address and port after the *connect* key word.

Now we start JExampleSim. To tell the mosaik-Java-API to run as TCP-server is done 
by starting it with "server" as second argument. The first command line argument is IP-address and port.  
The command line in our example looks like this:

.. code-block:: python

  java -cp JExampleSim.jar de.offis.mosaik.api.JExampleSim 1.2.3.4:5678 server

If we now execute demo_1.py we get the same :ref:`output <demo1_output>` as in 
our Python-example.

.. note::
    You can find the source code used in this tutorial in the 
    `mosaik-source-files <https://bitbucket.org/mosaik/mosaik>`_ in the folder 
    ``docs/tutorial/code``.
