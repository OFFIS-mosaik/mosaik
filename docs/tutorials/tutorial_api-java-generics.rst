.. _tutorial_api-java-generics:

===========================================================
Integrating a Model in Java with Generics / Annotations API
===========================================================

Additionally to the basic mosaik Java API, another API based on the basic one can be used, called `mosaik-java-api-generics <https://gitlab.com/mosaik/mosaik-api-java-generics>`_,
that contains some quality of life changes, for example automatic meta-model generation based on your model,
automatic model instantiation, input parsing via generics and automatic gathering of data for mosaik.

.. note:: When to use basic java api and when to use this api? If you want to use the flexibility from python, for example using all inputs. If you want to have a more type strict java-like experience, use this api instead.

This tutorial is also based on the Python tutorial :doc:`Python tutorial</tutorials/examplesim>` for the simple model and shows how to use the most features of this API.

Getting the Java API
====================

You can add the java package via maven or gradle, following the instructions at the `mosaik-java-generics-API package repository <https://gitlab.com/mosaik/mosaik-api-java-generics/-/packages/10720854>`_.

If you want to compile the jar yourself, you have to get the sources of the `mosaik-java-generics-API for Java <https://gitlab.com/mosaik/mosaik-api-java-generics>`_
which is provided on Gitlab. Clone it and put it in the development environment of your choice.

Creating the model
==================

The example model is again a replication from :ref:`model <the_simulator>`.
This model is annotated with @Model, which will tell the parser that this is a model for mosaik.
Normally, the simple class name will be used as model name. This can be customized by setting the value of the annotation.
The model annotation has several different sub-annotations that are useful to customize the behaviour of the of the model parser and
automatic class instantiation.
Some are also needed for some java versions to work, namely where constructor parameter names are not set.

.. note:: All fields MUST be a non-primitive type. This is needed for internal purposes for the input data parsing.
Else it could be possible that you read input values (for example 0 as demand) that were never set.

Annotated models, that are added to a simulator, will be searched for public fields and getter,
which will then be transformed into attributes.
For the mosaik params, a denoted constructor parameters will be used.
If more than one constructor are available, the constructor used must be annotated with @Model.Constructor.
You can rename constructor parameter by using @Model.Param("other_name").
This is especially useful if parameter naming is turned off (default for basic java).

The following example shows how to use the model annotation for the example model:

.. literalinclude:: code/src/de/offis/mosaik/api/utils/generics/AnnotatedExampleModel.java
   :language: java
   :lines: 6-35

Other usages annotations:

- @Model.Id: If you want to pass the model id into the model, you can annotate a constructor parameter with this annotation. The parameter will not be included into the meta-model.
- @Model.Suppress: If you want to use public getter or fields, which should only be used internally, you can annotate it with Suppress. These getter or fields will not be part of the meta-model created.

Creating the simulator
======================

The simulator implements an interface to the mosaik API.
This util package has two new simulators you can inherit from.
One for simulators with only one model and one for multi model simulation.
The reason to have two simulators is simpler use of generics for single models compared to multi-model simulations.
The simulators also separate entity model and input model.
Separating the input model from the entity model enables you to use only a subset of the entity model as input.

.. note:: Input models need a default constructor!
This is due to the input parsing where an initially empty model's fields will be filled iteratively.

Single model simulator
----------------------

The single model simulators fits perfectly for our small example.
We need to inherit from the ModelSimulator class and set the generic types.
The model generics are first the entity model (the created model instances) and second the input model.

.. literalinclude:: code/src/de/offis/mosaik/api/utils/generics/ExampleModelSim.java
   :language: java
   :lines: 13

The constructor must call the parent constructor with the simulator name, simulation type and entity and input model.
This will be then used to create the meta-model.

.. literalinclude:: code/src/de/offis/mosaik/api/utils/generics/ExampleModelSim.java
   :language: java
   :lines: 17-19


The second method that must be implemented is initialize.
It contains the same parameter as the original init method but without does not expect you to return the meta-model,
as this will be done automatically.

.. literalinclude:: code/src/de/offis/mosaik/api/utils/generics/ExampleModelSim.java
   :language: java
   :lines: 22-26

The last mandatory method is the modelStep, an abbreviation of the step method.
The parameter contain time, maxAdvance and parsed input from mosaik.
The input will be parsed into the generic input class passed to the simulator and put into a map which contains the model id and
a collection of InputMessages with sender and input class instance method.
The modelStep method for example will first sum the delta of all controller and then call the step method of the different models.

.. literalinclude:: code/src/de/offis/mosaik/api/utils/generics/ExampleModelSim.java
   :language: java
   :lines: 38-51

There are other optional methods that can be overridden.
- finishEntityCreation: Can be used to call auxiliary functions for models or modify the entity models and map itself.
- prepareGetData: Method will be called before the data for get_data will be gathered. Can be used if the mosaik model is only a DTO
- setupDone: Can be used to add functionality when all models are created.
- cleanup: Will be called after the simulation is finished, call super or else the entities will not be cleaned up!

The whole code for the simulator can be found here:

.. literalinclude:: code/src/de/offis/mosaik/api/utils/generics/ExampleModelSim.java
   :language: java
   :lines: 13-52

Multi model simulator
---------------------

The second simulator is designed to be able to simulate multiple models.
While this guide only covers an example with one model, the basic concept of this simulator should come clear.
Instead of using generics directly in the class, the simulator contains auxiliary methods to register methods for:
- Model registration
- Model creation finalization
- Input data processing

To show how to use a different input model,  the following model is used in this example:

.. literalinclude:: code/src/de/offis/mosaik/api/utils/generics/MessageModel.java
   :language: java
   :lines: 6-9

We first need to inherit from MultiModelInputSimulator and implement the constructor.
The constructor is the best place to register the models and processing methods.
For our example, we need to register our model and register an input step.
We can additionally register a model finishing method.

.. literalinclude:: code/src/de/offis/mosaik/api/utils/generics/MultiModelExampleSim.java
   :language: java
   :lines: 11-16

.. note:: You can only register models and methods when no simulation is running. Since there is currently no way to remove registered methods, try to only register them in the constructor.

First call the parent constructor with the simulator name and simulation type.
Additionally, already known entity models can be passed. They could also be registered via registerModel method.

registerStepMethod will take an input model class and a method to process the input data.
Parameters of the method are: time, Map of Map of InputMessage<T>, where T is the passed input model class.
In our method, we will sum all deltas for every model set it for our models.
We then return maxAdvance. This will make the simulationStep the step method which will dictate when we will be called again.
If you have a reason that a registered step method returns a time sooner than the one returned in simulationStep, the soonest time will be returned to mosaik.

.. literalinclude:: code/src/de/offis/mosaik/api/utils/generics/MultiModelExampleSim.java
   :language: java
   :lines: 30-41

registerFinishCreationMethod will take an entity model class and a function which passes a map of entity model instances,
just like the similar single model simulator method, but you need to return the entity map.
Since we have no additionally modifications to make, this method is empty and only there fore display purposes.

.. literalinclude:: code/src/de/offis/mosaik/api/utils/generics/MultiModelExampleSim.java
   :language: java
   :lines: 18-21

Two methods have to be implemented.
First, the initialize method, just like before in the single model simulator example, where the step size of the simulation is set:

.. literalinclude:: code/src/de/offis/mosaik/api/utils/generics/MultiModelExampleSim.java
   :language: java
   :lines: 23-28

Second, the simulationStep method needs to be implemented. Here, we gather all entities of the AnnotatedExampleModel class and call step for every instance.

.. literalinclude:: code/src/de/offis/mosaik/api/utils/generics/MultiModelExampleSim.java
   :language: java
   :lines: 43-47

You can also register methods for entity models before get_data will be called. The procedure is the same as for the other two register methods.

The whole code for the simulator:

.. literalinclude:: code/src/de/offis/mosaik/api/utils/generics/MultiModelExampleSim.java
   :language: java
   :lines: 8-48

Starting the simulator
----------------------

For the simulators to work, we need to add a main method that will start the simulation for the java side:

.. literalinclude:: code/src/de/offis/mosaik/api/utils/generics/SimulationStarter.java
   :language: java
   :lines: 9-20

Swap line 11 with the MultiModelExampleSimulator to use the second simulator.

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
            'cmd': 'java -cp JExampleSim.jar de.offis.mosaik.api.utils.generics.SimulationStarter %(addr)s',
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
    `mosaik-source-files <https://gitlab.com/mosaik/mosaik>`_ in the folder
    ``docs/tutorial/code``.

ParserHelper class
==================

As last note, the functions used to parse the mosaik data into models and creating the metamodel are available via the ParserHelper class.
Even if you don't want to use one of the simulators, this class has some QoL methods you may want to use.
Check the inbuilt java-docs of the library to learn more about the methods available and how to use them.