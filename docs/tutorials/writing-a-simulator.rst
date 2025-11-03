===================
Writing a simulator
===================

.. py:currentmodule:: mosaik_api_v3

.. important::

   If you write your simulator in a **Jupyter notebook**, using it in your scenario script will involve an additional step, as notebooks are not importable by default.
   This can be fixed by using installing and importing the `import-ipynb library <https://pypi.org/project/import-ipynb/>`_ at the start of your *scenario script* (not the simulator file).

   Alternatively, you can create the simulator as a normal Python file and only keep the scenario in a Notebook.

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
We will call the output *profit[EUR]*.
(We could technically use the € symbol, but that would make things harder to type for people with non-European keyboards.)

Finally, we need to decide which parts of our simulator should be configurable.
For this example, we will make the energy price a parameter, so that it is constant for the duration of the simulation (we could also add an entity to feed in changing energy prices during the simulation, for example).
We will also allow the user to pick the names of the entities.
This is not always necessary, but in this case, it will help in tracking which *PVProfits* entity belongs to which *PV* entity.


The meta dictionary
===================

All the design decisions for our simulator from the previous section culminate in our ``META``, which you may annotate with the type :class:`Meta` to get type checker support:

.. literalinclude:: code/profits_simulator.py
   :end-before: # end

The *api_version* always must be ``"3.0"``, and we determined above that our simulator should be hybrid.
For each model of our simulator, we create an entry in the *models* dict; here, this is just *PVProfits*.
In this dict, *public* determines whether entity of this model can be created by the user (in our case, they can).
The key *params* lists the parameters of our simulator.
(These are the names of the values that the user can or must provide when creating entities of this model.)

We list the attributes (the inputs and outputs that our simulator receives and sends *during* the simulation) under the keys *non-trigger* (for measurement inputs) and *non-persistent* (for event outputs).
We also need to specfy the keys *trigger* and *persistent* (for event inputs and measurement outputs, respectively), but both of them are simply empty lists, as our simulator has no such entities.

You might have noticed that we didn't specify how to give the energy price anywhere here.
This is a small wart in mosaik API: the way it is set up, parameters to the simulator itself (as opposed to its entities) need to be transmitted before the simulator has a chance to reply with its meta.
So even if the simulator did specify its own parameters, it would be too late.

Parameters to the simulator itself therefore need to be documented externally.
It is good practice to also document all other attributes and parameters in greater detail.


Initialization
==============

Our simulator is written as a subclass of :class:`mosaik_api_v3.Simulator`.
In the simulator class you will store the simulator's state and implement the mosaik methods that allow mosaik to advance your simulator through time.

Our simply simulator does not need much state:
For each *PVProfits* entity that the user creates in the scenario, we just need to store the corresponding profits.
We therefore create a dict called ``profits`` that will map each entity ID to the profits for that entity.

Each simulator also has two initialization methods.

First, there is the normal Python ``__init__`` method.
If your simulator needs parameters that do not come from the user's scenario file, you would provide them here.
In our case, we just create the ``profits`` dict and then call ``super().__init__`` with your simulator's meta.
``super().__init__`` will store the meta in the :attr:`~Simulator.meta` field.

The second initialization method is mosaik's own :meth:`~Simulator.init`.
It will be called when the user calls :meth:`~mosaik.scenario.World.start` the simulator in their scenario script.
This method will always receive the parameters ``sid`` for its own simulator ID in the scenario and ``time_resolution``, specifying how many seconds correspond to one mosaik step.
It will also receive additional parameters provided by the user.

Here, we added a ``price`` argument to our method, which the user should use to specify the energy price in EUR/MWh.
(We would specify this unit in the documentation.)

The :meth:`~Simulator.init` method frequently just stores this information and returns ``self.meta``.
(But it can do more, like set up database connections, etc.)

So far, we have this:

.. literalinclude:: code/profits_simulator.py
   :start-at: class Simulator
   :end-before: # end


Entity creation
===============

For users to be able to use our simulator, we must enable them to create entities in it, as that is the only thing they can connect in their scenario script.
Creating entities is the purview of the :meth:`~Simulator.create` method.
:meth:`~Simulator.create` receives the following arguments besides ``self``:

- ``num``---specifying how many entities should be created. (This allows creating entities in bulk without having to call :meth:`~Simulator.create` for each one.)
- ``model``---the name of the model.
- Other parameters specified by the user on creation, provided their names are listed in the *params* field of the model description for ``model`` in the meta; in our case, this is just ``eid``.

The method must return a list of exactly ``num`` instances of :class:`~mosaik_api_v3.CreateResult`.
Each :class:`~mosaik_api_v3.CreateResult` is a Python dict with the fields *eid* and *type*.
(As it is a normal dict, the name :class:`~mosaik_api_v3.CreateResult` will only appear in type annotations.)

The *eid* field specifies the entity's **entity ID**.
It will be used by mosaik to communicate to your simulator which input data is meant for which entity, and vice versa by your simulator to indicate which entity produced a given ountput.
*As such, all entity IDs returned by your simulator must be unique, even accross multiple calls to* :meth:`~Simulator.create` *during the same simulation.*

The *type* field must mirror the value given in ``model``.
(It exists for simulators using child entities, see :doc:`/how-tos/existing-topologies`.)

Because we want to allow users to set the entity ID, our :meth:`~Simulator.create` method is a bit involved.
First, we sort out the entity ID business:

.. literalinclude:: code/profits_simulator.py
   :start-at: def create
   :end-before: # end

When the user creates entities, they can give the parameter ``eid``.
There are three cases:

- They might not specify it (or specify `None`).
  In this case, we create entity IDs looking like *PVProfits-42*.
  The numbers start with the number of already-existing entities.
  This ensures that we will not create the same entity ID twice, even if :meth:`~Simulator.create` is called multiple times.
  (This might run into problems if the user specifies entity IDs some of the time but we will catch those later.)
- They might specify a single string.
  We only allow this if they also just create a single entity.
- They might specify a list of entity IDs.
  In this case, we check that it has the right length.

At the end of this process, ``eid`` is a list, and it contains ``num`` IDs.

Using this list, we then create the entities:

.. literalinclude:: code/profits_simulator.py
   :start-at: new_entities:
   :end-at: return new_entities

For each entity ID we first make good on our promise above to not repeat ourselves.
Then we create the new entity, which can take many forms, depending on the complexity of your simulator.
As ours is quite simple, we just need to add the entity ID as a key to our ``profits`` dict to "create" it.
(We will use the associated value later to store the profits.)
In more complex cases, it is common to implement a class representing an individual entity and to create and store and instance of that class to create an entity.

Finally, we also need to inform mosaik about the entity.
To this end, we add a dict of a certain structure (namely the one given by :class:`~mosaik_api_v3.CreateResult`) to the ``new_entities`` list.
The *eid* that we specify there is the only thing that mosaik uses to identify our entity and associate inputs and outputs to it.


Stepping
========

Next, we need to specify what our simulator does during the simulation.
The place to do this is the :meth:`~Simulator.step` method.
Besides ``self``, it gets three arguments:

- ``time``---the current :term:`simulation time`.
- ``inputs``---the inputs to our simulator for this step.
- ``max_advance``---which is only relevant for advanced event-based simulators, see :doc:`/how-tos/max-advance`.

This method of our simulator will automatically be called at time 0, and then again each time we return a non-``None`` value from this method.
(If our simulator had trigger attributes, those could result in additional calls to :meth:`~Simulator.step`, see :doc:`/explanations/measurements-and-events`.)

To perform our step, we need to read the data from the ``inputs`` argument.
This is actually a thrice-nested dictionary:

- The outer-most level has entity IDs of our simulator as keys.
- The middle level has attributes of those entities as keys.
- The inner-most level has full IDs of source simulators.
  These can often be ignored, unless your simulator has special needs that require it to know who sent the data.
  (Usually, only simulators writing data to some file or database should use this.)
- The values at the last level are the actual inputs.

For example, for our simulator, ``inputs`` could look like this::

   {
       "PVProfits-0": {
           "P[MW]": {
               "PV.PV-0": 0.5,
           },
       },
       "PVProfits-1": {
           "P[MW]": {
               "PV.PV-1": 1.2,
               "PV.PV-2:" 0.8,
           },
       },
   }

Here, the user has connected two *PV* entities to our *PVProfits-1* entity.
(Namely, the entities *PV.PV-1* and *PV.PV-2*.)
It is up to our simulator how to deal with duplicate values.
If there is no sensible resolution, a simulator should raise an Error.
However, for power values, it is reasonable to simply add them.

Once we have our power input, we can determine our profits with the formula

.. math::
   \mathsf{P[MW]} \times \frac{\mathsf{step\_size} \times \mathsf{time\_resolution}}{3600} \times \mathsf{price}

Here, :math:`\mathsf{step\_size} \times \mathsf{time\_resolution}` gives the length of a step in seconds, which we divide by :math:`3600` to get a value in hours, compatible with our price unit.
We store these profits in ``self.profits``, sorted by entity.

Finally, we return ``time + self.step_size`` as the step at which we want to be called next:

.. literalinclude:: code/profits_simulator.py
   :pyobject: Simulator.step

Having calculated the profits, we now need to pass them to mosaik.
For this, there is a second method, :meth:`~Simulator.get_data`.
Usually, mosaik will call this immediately after the call to :meth:`~Simulator.step` has returned, except when our simulator's output is not used by any other simulator.

:meth:`~Simulator.get_data` gets called with an :class:`~mosaik_api_v3.OutputRequest`, which is just a dictionary mapping entity IDs of our simulator to attribute names.
Our simulator should return output for the given attributes of those entities.
There are two cases here:

- If the attribute is :ref:`persistent`, output should always be provided.
- If the attribute is :ref:`non-persistent` and the corresponding event occurred, output should be provided to indicate that occurrence to mosaik.

The :class:`~mosaik_api_v3.OutputRequest` will only list those attributes that are connected to other simulators.
However, if it makes implementing your simulator simpler (and the overhead is acceptable), you can also return output for non-requested attributes, which mosaik will simply ignore.
(Output for non-existing attributes will result in at error, though, as this indicates a typo in the :meth:`~Simulator.get_data` implementation.)

As output, we produce a dict of dicts, mapping each entity ID to a dict mapping attribute names to values.
In our case, we simply send out all the profits that currently exist.
Then we reset them so that we don't send the same profits again later.
(Though, due to the calling behaviour of mosaik, this should not happen, anyway.)

.. literalinclude: code/profits_simulator.py
   :pyobject: Simulator.get_data

This concludes the writing of our toy simulator.


Adapting our scenario
=====================

Finally, it is time to integrate our new simulator into our simulation from the :doc:`previous tutorial <a-first-scenario>`.
It will end up looking like this:

.. figure:: /_static/tutorial2.png
   :width: 600
   :align: center
   :alt: A scenario consisting of the five simulators Weather, PV, Grid and Profits (both receiving input from PV), and Output (receiving input from both Grid and Profits)

   The updated scenario

We add it to the ``SIM_CONFIG``

.. literalinclude:: code/scenario_2.py
   :start-at: "Profits": {
   :end-at: "Profits": {

and start it together with the other simulators:

.. literalinclude:: code/scenario_2.py
   :start-at: profitssim =
   :end-at: profitssim =

We create a *PVProfits* entity for each PV entity by first creating a list of their eids and then using the :meth:`~mosaik.scenario.ModelMock.create` function:

.. literalinclude:: code/scenario_2.py
   :start-at: pv_profit_eids =
   :end-before: # end

Finally, we connect the PV systems to our profit simulator, and the profit simulator to the output simulator:

.. literalinclude:: code/scenario_2.py
   :start-after: # connect profits
   :end-before: # end


Where to go from here
=====================

When you are implementing an actual simulator, there are a couple of additional topics that might be of interest to you:

- To learn more about the distinction between measurements and events in mosaik, see :doc:`/explanations/measurements-and-events`.
- For efficient simulators with trigger inputs (i.e., events as inputs), you often need to know how far you can advance without potentially getting interrupted. See :doc:`/how-tos/max-advance` for more on this.
- If your simulator communicates with other simulators at a high frequency (either to perform a joint convergence algorithm, or because it is implementing a control algorithm that needs to communicate with other units), you might want to learn about same-time loops and :doc:`/explanations/tiered-time`.
- This tutorial uses mosaik's simulator API for Python.
  To learn more about which other simulator APIs exist, and for the necessary information to implement the simulator API for new programming languages, see :doc:`/mosaik-api/index`.

If you have questions about any of this (or anything else concerning mosaik), feel free to contact us on `GitHub discussions <https://github.com/orgs/OFFIS-mosaik/discussions>`_.
All levels of questions are welcome.
