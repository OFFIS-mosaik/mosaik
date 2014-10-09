========
Overview
========

This section describes how mosaik works without going into too much detail.
After reading this, you should have a general understanding of what mosaik does
and how to proceed in order to implement the mosaik API or to create
a :term:`simulation scenario <scenario>`.


What's mosaik supposed to do?
=============================

Mosaik's main goal is to use existing :term:`simulators <simulator>` in
a common context in order to perform a coordinated simulation of a given (Smart
Grid) scenario.

That means that all simulators (or other tools and hardware-in-the-loop)
involved in a simulation usually run in their own process with their own event
loop. Mosaik just tries to synchronize these processes and manages the exchange
of data between them.

To allow this, mosaik

#. provides an API for simulators to communicate with mosaik,

#. implements handlers for different kinds of simulator processes,

#. allows the modelling of simulation scenarios involving the different
   simulators, and

#. schedules the step-wise execution of the different simulators and manages
   the exchange of data (:term:`data-flows <data-flow>`) between them.

Although mosaik is written in Python 3, its simulator API completely language
agnostic. It doesn't matter if your simulator is written in Python 2, Java,
C, matlab or anything else.


A simple example
----------------

.. image:: _static/mosaik-slide.*
   :width: 100%
   :align: center
   :alt: mosaik

We have simulators for households (blue icon) and for photovoltaics (green).
We're also gonna use a load flow analysis tool (grey), and a monitoring and
analysis tool (yellow).

First, we have to implement the mosaik API for each of these "simulators". When
we are done with this, we can create a scenario where we connect the households
to nodes in the power grid. Some of the households will also get a PV module.
The monitoring / analysis tool will be connected to the power grid's
transformer node. When we connect all these :term:`entities <entity>`, we also
tell mosaik about the data-flows between them (e.g., active power feed-in from
the PV modules to a grid node).

When we finally start the simulation, mosaik requests the simulators to perform
simulation steps and exchanges data between them according to the data-flows
described in the scenario. For our simple example, that would roughly look like
this:

1. The household and PV simulator perform a simulation step for an interval
   *[0, t[*.

2. Mosaik gets the values for, e.g., *P* and *Q* (active and reactive power)
   for every household and every PV module.

3. Mosaik sets the values *P* and *Q* for every node of the power grid based on
   the data it collected in step 2. The load flow simulator performs
   a simulation step for *[0, t[* based on these inputs.

4. Mosaik collects data from the load flow simulator, sends it to the
   monitoring tool and lets it also perform a simulation step for *[0, t[*.

5. Now the whole process is repeated for *[t, t+i[* and so forth until the
   simulation ends.

In this example, all simulators had the same step size *t*, but this is not
necessary. Every simulator can have its one step size (which may even vary
during the simulation). It is also possible that a simulator (e.g., a control
strategy) can set input values (e.g., a schedule) to another simulator (e.g.,
for "intelligent" consumers).


Mosaik's main components
========================

Mosaik consists of four main components that implement the different aspects of
a co-simulation framework:

#. The **mosaik Sim API** defines the communication protocol between
   :term:`simulators <simulator>` and mosaik.

   Mosaik uses plain network sockets and JSON encoded messages to communicate
   with the simulators. We call this the *low-level API*. For some programming
   languages there also exists a *high-level API* that implements everything
   networking related and offers an abstract base class. You then only have to
   write a subclass and implement a few methods.

   :doc:`Read more … <mosaik-api/index>`

#. The **Scenario API** provides a simple API that allows you to create
   your simulation scenarios in pure `Python <https://python.org>`_ (yes, no
   graphical modelling!).

   The scenario API allows you to start simulators and instantiate models from
   them. This will give you *entity sets* (sets of :term:`entities <entity>`).
   You can then connect the entities with each other in order to establish
   :term:`data-flows <data-flow>` between the simulators.

   Mosaik allows you both, connecting one entity at a time as well as
   connecting whole entity sets with each other.

   :doc:`Read more … <scenario-definition>`

#. The **Simulator Manager** (or shorter, **SimManager**) is responsible for
   handling the simulator processes and communicating with them.

   It is able to *a)* start new simulator processes, *b)* connect to already
   running process instances, and *c)* import a simulator module and execute
   it *in-process* if it's written in Python 3.

   The in-process execution has some benefits: it reduces the amount of memory
   required (because less processes need to be started) and it avoids the
   overhead of (de)serializing and sending messages over the network.

   External processes, however, can be executed in parallel which is not
   possible with in-process simulators.

   :doc:`Read more … <simmanager>`

#. Mosaik's **simulator** uses the event-discrete simulation library `SimPy
   <https://simpy.readthedocs.org>`_ for the coordinated simulation of
   a scenario.

   Mosaik is able to handle simulators with different step sizes. A simulator
   may even vary its step size during the simulation.

   Mosaik is able to track the dependencies between the simulators and only
   lets them perform a simulation step if necessary (e.g., because its data is
   needed by another simulator). It is also able to let multiple simulators
   perform their simulation step in parallel if they don't depend on each
   other's data.

   :doc:`Read more … <scheduler>`
