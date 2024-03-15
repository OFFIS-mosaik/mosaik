We will now extend the simulation from the previous tutorial by writing our own simulator.
In this first version, our simulator will calculate how much money a set of PV systems would generate (given some fictional energy prices) and send this information on to our output simulator as well.

We will implement this simulator in Python, using the so-called *high-level API* (see here for more information on mosaik's APIs).
To do this, one writes a subclass of ``mosaik_api_v3.Simulator``.
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

The ``Simulator`` class has four main methods: ``init``, ``create``, ``step``, and ``get_data``. 
(There are a few additional methods that you can implement for special purposes.)

-  ``init`` is the first method that mosaik will call when starting (or connecting to) a simulator. 
   This happens when the user uses ``world.start`` in their scenario script.
   The simulator must return its so-called *meta* which is a data structure that describes how the simulator can be used.
   In particular, it contains the simulator's type and a list of all of the simulator's models and their parameters and attributes.
-  ``create`` is called whenever the user creates entities in their scenario script.
   The simulator can store the entities however it wants (as separate objects, rows in some table, names in a list, etc.) but it must create and return to mosaik a list of entity IDs together with their types, children and relations to other entities in the same simulator.
-  ``step`` is called during the simulation whenever the simulator should perform its next calculation. 
   The simulator must return the time when it wants to run the next time, or ``None`` if it only wants to run on new events (see [[#Types of Simulators]] below).
-  ``get_data`` is called during the simulation whenever mosaik needs data from the simulator, usually directly after `step` has returned.
   mosaik might request only parts of the data that the simulator could provide to reduce the amount of data that needs to be sent back and forth.

Attributes and Types of Simulators
==================================

Before we can get to implementing, we need to understand types of mosaik simulators a bit more.
As you know by now, a mosaik scenario consists of a bunch of entities which are connected via their attributes.
The author of a simulator gets to define the attributes by listing their names in the meta.
Based on the connections in the scenario, the simulator will then receive input data tagged with these attribute names.
Likewise, it is expected to tag its output in the same way.
We will see how this is done on a technical level in the sections on the ``step`` and ``get_data`` methods.

Choosing your simulator's attributes is one of the first steps in designing it.
In addition to its name and whether it is used for input or output (or both), there is a third aspect to each attribute.
Namely, it falls into one of two broad categories, *measurements* or *events*:

-  Measurements are values that exist continuously, i.e. it always makes sense to ask for their current value.
   Common examples would include the current time or physical measurements like the current DNI or the power output of a PV system.
   At any time in your simulation, you might reasonably ask: “What is the current value of this measurement?”
   (These were the only kind of attribute that existed in mosaik prior to version 3.)
-  Events happen at certain points in time.
   When an attribute is marked as an event, it might never happen, or occasionally, or several times at once.
   Whenever it does happen, there is a value attached to that occurrence.
   So it makes sense to ask for the value of an occurrence, but not for the current value of an event, because there might not be one currently at all or there might be several at the same time.
   Examples of events might include the points in time where a certain measurement changes its sign or commands sent from one simulator to another.

