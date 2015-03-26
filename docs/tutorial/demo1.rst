.. _demo1:

.. currentmodule:: mosaik.scenario

================================================
Creating and running simple simulation scenarios
================================================

We will now create a simple scenario with mosaik in which we use also use
a simple data collector to get some nice output from our simulation. That
means, we will instantiate a few ExampleModels and a data monitor. We will
then connect the model instances to that monitor and simulate that for some
time.


Configuration
=============

You should define the most important configuration values for your simulation
as "constants" on top of your scenario file. This makes it easier to
see what's going on and change the parameter values.

Two of the most important parameters that you need in almost every simulation
are the *simulator configuration* and the *duration* of your simulation:

.. literalinclude:: code/demo_1.py
   :lines: 6-16

The *sim config* specifies which simulators are available and how to start
them. In the example above, we list our *ExampleSim* as well as *HDF5* (the
names are arbitrarily chosen). For each simulator listed, we also specify how
to start it.

Since our example simulator is, like mosaik, written in Python 3, mosaik can
just import it and execute it in-process. The line ``'python':
'simulator_mosaik:ExampleSim'`` tells mosaik to import the package
``simulator_mosaik`` and instantiate the class ``ExampleSim`` from it.

The data collector will be started as external process which will communicate
with mosaik via sockets. The line ``'cmd': 'python collector.py %(addr)s'``
tells mosaik to start the simulator by executing the command ``python
collector.py``. Beforehand, mosaik replaces the placeholder ``%(addr)s`` with
its actual socket address HOSTNAME:PORT so that the simulator knows where to
connect to.

The section about the :doc:`Sim Manager </simmanager>` explains all this in
detail.

Here is the complete file of the data collector:

.. literalinclude:: code/collector.py

The World
=========

The next thing we do is instantiating a :class:`World` object. This object will
hold all simulation state. It knows which simulators are available and started,
which entities exist and how they are connected. It also provides most of the
functionality that you need for modelling your scenario:

.. literalinclude:: code/demo_1.py
   :lines: 2,4,18-19


The scenario
============

Before we can instantiate any simulation models, we first need to start the
respective simulators. This can be done by calling :meth:`World.start()`. It
takes the name of the simulator to start and, optionally, some simulator
parameters which will be passed to the simulators ``init()`` method. So lets
start the example simulator and the HDF5 database adapter:

.. literalinclude:: code/demo_1.py
   :lines: 21-23

We also set the *eid_prefix* for our example simulator and some configuration
values for the database. It will collect data every minute until the simulation
ends. What gets returned by :meth:`World.start()` is called a *model factory*.

We can use this factory object to create model instances within the respective
simulator. In your scenario, such an instance is represented as an
:class:`Entity`. The model factory presents the available models as if they
were classes within the factory's namespace. So this how we can create one
instance of our example model and one database instance:

.. literalinclude:: code/demo_1.py
   :lines: 25-27

The *init_val* parameter that we passed to ``ExampleModel`` is the same as in
the ``create()`` method of our Sim API implementation. Similarly, the database
has a parameter for its filename.

Now, we need to connect the example model to the monitor. That's how we tell
mosaik to send the outputs of the example model to the monotir.

.. literalinclude:: code/demo_1.py
   :lines: 29-30

The method :meth:`World.connect()` takes one entity pair – the source and the
destination entity, as well as a list of attributes or attribute tuples. If you
only provide single attribute names, mosaik assumes that the source and
destination use the same attribute name. If they deffer, you can instead pass
a tuple like ``('val_out', 'val_in')``.

Usually, you will neither create single entities nor connect single entity
pairs, but work with large(r) sets of entities. Mosaik allows you to easily
create multiple entities with the same parameters at once. It also provides
some utility functions for connecting sets of entities with each other. So lets
create nine more entities and connect them to our monitor:

.. literalinclude:: code/demo_1.py
   :lines: 3-4,32-34

Instead of instantiating the example model directly, we called its static
method ``create()`` and passed the number of instances to it. It returns a list
of entities (nine in this case). We used the utility function
:func:`mosaik.util.connect_many_to_one()` to connect all of them to the
database. This function has a similar signature as :meth:`World.connect()`, but
the first two parameters are a *world* instance and a set (or list) of entities
that are all connected to the *dest_entity*.

Mosaik also provides the function :func:`mosaik.util.connect_randomly()`. This
method randomly connects one set of entities to another set. These two methods
should cover most use cases. For more special ones, you can implement custom
functions based on the primitive :meth:`World.connect()`.


The simulation
==============

In order to start the simulation, we call :meth:`World.run()` and specify for
how long we want our simulation to run:

.. literalinclude:: code/demo_1.py
   :lines: 36-37

Executing the scenario script will then give us the following output:

.. literalinclude:: code/demo_1.out
   :lines: 1-9,30-


Summary
=======

This section introduced you to the basic of scenario creation in mosaik. For
more details you can check the :doc:`guide to scenarios
</scenario-definition>`.

For your convenience, here is the complete scenario that we created in this
tutorial. You can use this for some more experiments before continuing with
this tutorial:

.. literalinclude:: code/demo_1.py

The next part of the tutorial will be about integrating control mechanisms into
a simulation.
