===================
Writing a simulator
===================

.. py:currentmodule:: mosaik_api_v3

We will now extend the simulation from the previous tutorial by writing our own simulator.
In this first version, our simulator will calculate how much money a set of PV systems would generate (given some fictional energy prices) and send this information on to our output simulator as well.

We will implement this simulator in Python, using the so-called *high-level API*. (See here for more information about the different mosaik APIs: :doc:`/mosaik-api/index`.)

To do this, we will write a subclass of :py:class:`mosaik_api_v3.Simulator`.
This base class is part of the ``mosaik-api-v3`` package, which you can install from PyPI.
If you are using the same environment as in the previous tutorial, this package will already be installed.
However, it is also possible to just install this package (without the rest of mosaik) for situations where you are just writing a simulator and no scenario in the same environment.
If you plan on publishing your simulator, only depending on the API is good practice.

.. admonition:: Why v3?

   The name of the mosaik API package contains the version number of the mosaik API, which is currently 3.
   When a new version of mosaik is released that offers a new version of the API, this API will be published as ``mosaik-api-v4``, and so on.
   This allows you to have simulators using the old and new API installed in the same environment.


Overview of the simulator class
===============================

The :py:class:`Simulator` class has four main methods: :py:meth:`~Simulator.init`, :py:meth:`~Simulator.create`, :py:meth:`~Simulator.step`, and :py:meth:`~Simulator.get_data`.
(There are a few additional methods that you can implement for special purposes.)

-  :py:meth:`~Simulator.init` is the first method that mosaik will call when starting (or connecting to) a simulator.
   This happens when the user uses :py:meth:`world.start <mosaik.scenario.World.start>` in their scenario script.
   The simulator must return its so-called *meta* which is a data structure that describes how the simulator can be used.
   In particular, it contains the simulator's type and a list of all of the simulator's models and their parameters and attributes.
-  :py:meth:`~Simulator.create` is called whenever the user creates entities in their scenario script.
   The simulator can store the entities however it wants (as separate objects, rows in some table, names in a list, etc.) but it must create and return to mosaik a list of entity IDs together with their types, children and relations to other entities in the same simulator.
-  :py:meth:`~Simulator.step` is called during the simulation whenever the simulator should perform its next calculation.
   The simulator must return the time when it wants to run the next time, or ``None`` if it only wants to run on new events (see :ref:`attrs-and-types`  below).
-  :py:meth:`~Simulator.get_data` is called during the simulation whenever mosaik needs data from the simulator, usually directly after :py:meth:`~Simulator.step` has returned.
   mosaik might request only parts of the data that the simulator could provide to reduce the amount of data that needs to be sent back and forth.


.. _attrs-and-types:

Attributes and Types of Simulators
==================================

Before we can get to implementing, we need to understand types of mosaik simulators a bit more.
As you know by now, a mosaik scenario consists of a bunch of entities which are connected via their attributes.
The author of a simulator gets to define the attributes by listing their names in the meta.
Based on the connections in the scenario, the simulator will then receive input data tagged with these attribute names.
Likewise, it is expected to tag its output in the same way.
We will see how this is done on a technical level in the sections on the :py:meth:`~Simulator.step` and :py:meth:`~Simulator.get_data` methods.

Choosing your simulator's attributes is one of the first steps in designing it.
In addition to its name and whether it is used for input or output (or both), there is a third aspect to each attribute.
Namely, it falls into one of two broad categories, *measurements* or *events*:

-  :index:`Measurements <measurement>` are values that exist continuously, i.e. it always makes sense to ask for their current value.
   Common examples would include the current time or physical measurements like the current DNI or the power output of a PV system.
   At any time in your simulation, you might reasonably ask: “What is the current value of this measurement?”
-  :index:`Events <event>` happen at certain points in time.
   When an attribute is marked as an event, it might never happen, or occasionally, or several times at once.
   Whenever it does happen, there is a value attached to that occurrence.
   So it makes sense to ask for the value of an occurrence, but not for the current value of an event, because there might not be one currently at all or there might be several at the same time.
   Examples of events might include the points in time where a certain measurement changes its sign or commands sent from one simulator to another.

You can read more about this in :doc:`/explanations/measurements-and-events`.

Our simulator will take in the power output of the PV systems in the simulation.
The power output is always defined (even if it might be 0 at night), so it makes sense to treat it as a measurement.
We want to send out the profit we make during the last interval.
We get this profit only once, so it is sensible to treat this as an event.
Alternatively, we also track our entire profit (from the beginning of the simulation) so far.
In this case, a measurement would be the right choice for this attribute.

As we want to use both measurements and events in our simulator, our simulator type is *hybrid*.
To be able to track each PV system individually, we will package the profit tracking for one such system into an entity, which we will name *PVProfits*.
For the input attribute, we choose the name *P[MW]*.
This lines up nicely with the name of the output attribute of our PV simulator, so connections in the scenario can be written more concisely.
We will call the output *profits[EUR]*.
(We could technically use the € symbol, but that would make things harder to type for people with non-European keyboards.)

Finally, we need to decide which parts of our simulator should be configurable.
For this example, we will make the the energy price a parameter, so that it is constant for the duration of the simulation (we could also add an entity to feed in changing energy prices during the simulation, for example).
We will also allow the user to pick the names of the entities.
This is not always necessary, but in this case, it will help in tracking which *PVProfits* entity belongs to which *PV* entity.


The meta dictionary
===================

All the design decisions for our simulator from the previous section culminate in our ``META``:

.. literalinclude:: code/profits_simulator.py
   :end-before: # end
