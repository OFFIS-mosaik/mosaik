=======================
Measurements and Events
=======================

mosaik supports two different kinds of values: measurements and events.

.. index:: ! measurement

Conceptually, a **measurement** is a value that exists continuously throughout the simulation. Most physical quantities, like the voltage at a certain bus in the grid fall into this category.

.. index:: ! event

**Events**, on the other hand, exists only at certain points in time. Common examples of events are control signals and other types of messages.

.. index::
   ! pair: attribute; persistent
   ! pair: attribute; non-persistent

While measurements often represent values that would change continuously in the real world, in our simulations, we need to discretize them.
To this end, mosaik simply considers the most recent value produced for that measurement to be valid until it is overwritten by a newer value.
Due to this behaviour, measurement outputs of simulators are called **persistent attributes**, with all other outputs considered **non-persistent**.

.. index::
   ! pair: attribute; trigger
   ! pair: attribute; non-trigger

Events can be represented more accurately, as they are simply given by a time together with an associated value.
Because it is often necessary to react to an event immediately, a simulator's :py:meth:`~mosaik_api_v3.Simulator.step` method is invoked whenever one of its attributes receives an event.
For this reason, event inputs to simulators are called **trigger attributes**, with all other inputs considered **non-trigger**.

The names *persistent* and *trigger* are essentially a bit of a historical accident, but they persist in a lot of writing about mosaik.
As we can not trigger a universal rewrite, they're here to stay, to some degree.

While the technical representation of measurements and events is very similar (because of the discretization of measurements), it usually does not make much sense to use a measurement where an event is expected or vice versa.
There is one big exception to this: simulators that collect the output of a simulation.
In this case, we are often interested in every value that is produced at any time, so we want to trigger the output simulator whenever new inputs are available.
Therefore, mosaik will accept connections from a persistent attribute to a trigger attribute.
On the other hand, we do not know of any sensible situations in which you would want to interpret an event output as a measurement input.
(A simulator can reasonably expect to receive data on each of its measurement inputs every time, but events do not give this guarantee.)
Therefore, mosaik will warn you if you set up connections like this.

On more word of warning:
Because mosaik does not know whether a simulator is an output collector, it will also silently accept measurement-to-event connections if the destination simulator is not an output simulator.
This can unfortunately lead to subtle bugs where a simulator receives the same value multiple times (as the measurement output is considered persistent) and incorrectly interprets this as a new event each time it is called.
We hope to provide better semantics for this in the future.


.. index::
   ! simulator type

Types of simulators
===================

The different types of values are coupled to the different types of simulators mosaik supports.

.. index::
   ! pair: simulator type; time-based

First, there are **time-based** simulators.
Before mosaik 3, this was the only type of simulator.
In a time-based simulator, all values are measurements and it is an error to mark attributes as trigger or non-persistent.
Because a time-based simulator has no trigger attributes, it will only run on its self-scheduled steps; with the sole exception that it will also be stepped at time 0, to start the whole process.

.. index::
   ! pair: simulator type; event-based

With mosaik 3, **event-based** simulators were introduced to mosaik.
In an event-based simulator, every value is an event, and it is an error to mark attributes as non-trigger or persistent.
An event-based simulator will not automatically be stepped at time 0.
Usually, you will connect it in such a way that some other simulator will wake it up by sending it data at some point.
However, the user can also call the :py:meth:`~mosaik.scenario.World.set_initial_event` method on the simulator in their scenario to schedule an event-based simulator's first step.
Once started, event-based simulators may (but are not required to) schedule steps for themselves by returning a next stepping time from their :py:meth:`~mosaik_api_v3.Simulator.step` method.

.. index::
   ! pair: simulator type; hybrid

Last, there are **hybrid** simulators.
By default, these behave pretty much like time-based simulators.
However, individual attributes may be explicitly marked as *trigger* or *non-persistent*, in which case their values will be treated as events by mosaik.
Usually, if there are both time-based and event-based simulators in your simulation, you will need hybrid simulators in-between to make the appropriate translations between events and measurements.
