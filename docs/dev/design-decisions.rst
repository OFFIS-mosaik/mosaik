==============================
Discussion of design decisions
==============================

On this page, we discuss some of the design decisions that we made. This should
explain why some features are (not) present and why they work the way that they
work.

.. note::

   For the sake of readability, some concepts are simplified in the following
   sections. For example, the snippet ``connect(A, B)`` means we're connecting
   some entities of a simulator *A* to some entities of simulator *B*;
   *simulator* and *entity* are used as if they were the same concept;
   *A.step()* means, that mosaik calls the *step()* function of
   simulator/entity *A*.

Here are the topics:

.. contents::
   :local:

.. _circular-data-flows:

Circular data-flows
===================

Circular data-flows were one of the harder problems to solve.

When you connect the entities of two simulators with each other, mosaik tracks
the new dependency between these simulators:

.. code-block:: python

   connect(A, B)

*A* would now provide input data for *B*. When mosaik runs the simulation, the
step for a certain time *t* would first be computed for *A* and then for *B*
with the inputs of *A*.

In order to connect control strategies (like multi-agent systems) with
to-be-controlled entities, you usually need a circular data-flow. The entity
provides state information for the controller which in turn sends new commands
or schedules to the controlled entity. The naïve way of doing this would be:

.. code-block:: python

   connect(A, B, 'state')
   connect(B, A, 'schedule')

*A* would receive schedules via the inputs of *A.step()*. In *A.step()*, it
would compute new state information which mosaik would get via *A.get_data()*.
Mosaik would forward this to the inputs of *B.step()*. *B.step()* would
calculate some schedules, which mosaik would again get via *B.get_data()* and
pass to *A.step()* …

The question that arise here is: Which simulator do we step first – *A* or *B*?
Mosaik has no clue.  You *could* say that *A* needs to step first, because the
data-flow from *A* to *B* was established first. However, if you re-arrange
your code and (accidentally) flip both lines, you would get a different
behavior and a very hard to find bug.

What do we learn from that? We need to explicitly tell mosaik how to resolve
these cycles and prohibit normal circular data-flows as in the snippet above.

Mosaik provides two ways for this. The first is via time-shifted connections:

.. code-block:: python

   connect(A, B, 'state')
   connect(B, A, 'schedule', time_shifted=True)

This tells mosaik how to resolve the cycle and throws an error if you
accidentally flip both lines.

Theoretically, we could be done here. But we aren't. The data-flows in the
example above are passive, meaning that *A* and *B* compute data hoping that
someone will use them. This abstraction works reasonably well for normal
simulation models, but control mechanism usually have an *active* role. They
actively decide whether or not to send commands to the entities they control.

Accordingly, mosaik provides ways for control mechanisms and monitoring tools
to actively collect more data from the simulation and set data to other
entities. These means are implemented as :ref:`asyncronous requests
<async_requests_overview>` that a simulator can perform during its step.
Similar to the cyclic data-flows, this requires you to tell mosaik about it to
prevent some scheduling problems:

.. code-block:: python

   connect(A, B, async_requests=True)

This prevents *A* from stepping too far into the future so that *B* can get
additional data from or set new data to *A* in *B.step()*.

Since you can set data via an asynchronous request, you can implement cyclic
data-flows with it:

.. code-block:: python

   connect(A, B, 'state', async_requests=True)

The implementation of *A.step()* and *A.get_data()* would be the same. In
*B.step()* you would still receive the state information from *A* and compute
the schedules. However, you wouldn't store them somewhere so that
*B.get_data()* can return them. Instead, you would just pass them actively to
*set_data()*. Mosaik stores that data in a special input_buffer of *A* which
will be added to the input of *A*'s next step.

So to wrap this up, there are two possibilities to achieve cyclic data-flows:

1. Passive controller:

   .. code-block:: python

      connect(A, B, 'state')
      connect(B, A, 'schedules', time_shifted=True)

   *B.step()* computes schedules and caches them somewhere. Mosaik gets these
   schedules via *B.get_data()* and sends them to *A*.

   If you forget to set the ``time_shifted=True`` flag, mosaik will raise an
   error at *composition time*.

   If you forget the second *connect()*, nothing will happen with the
   schedules. You may not notice this for a while.

2. Active controller:

   .. code-block:: python

      connect(A, B, 'state', async_requests=True)

   *B.step()* computes schedules and immediately passes them to *set_data()*.
   Mosaik sends them to *A*.

   If you forget to set the ``async_requests=True`` flag, mosaik will raise an
   error at *simulation time*.


Same-time loops for control cycles
==================================

The first implementation of same-time loops was pretty ad-hoc and therefore showed some difficult-to-explain behavior.
In particular, the order in which simulators in a same-time loop would trigger each other depended in subtle ways on the order in which connections were established.
(The execution order was governed by the *rank* of a simulator, which was calculated using a topological sort method from networkx.)

As a first solution, we attempted a concept of dense time, where each internal time stamp had two components, called *time* and *micro step*.
Only the time component is communicated to the simulators, whereas the micro step component is only used internally.
Progress along weak connections would only increase the micro step component, allowing simulators to perform multiple steps in one time step, while still preserving an order for all steps.

Unfortunately, a very common control structure that usually happened to work under the old scheme was not possible anymore:
The simplest version of the case in question is when there are two simulators that communicate via a same-time loop and which then send the result of their negotiation to a third simulator.
Because users would normally create the connections for the negotiation part earlier in their scenario, the corresponding same-time loop would run first, leading to the expected result.
With the dense-time setup, the third simulator would instead run at micro step 0, and thus only receive the results of the first round of negotiation.

To resolve this problem, we introduce a concept of *simulator groups*.
A user can create a group in their script using a ``with`` statement like

.. code-block:: python

   with world.group():
       world.start("SimulatorA")
       world.start("SimulatorB")

All simulators started in the ``with`` block are automatically added to the group.
Users can nest groups by nesting the ``with world.group()`` blocks.
(Using the ``with`` statement has the advantage that users cannot nest the groups incorrectly.)

Each group adds an additional tier to the internal times used for simulators contained within, leading to a concept of *tiered time*.
(The simulators still only get to see the highest level.)
When a connection leaves a group (i.e. leads from a simulator in a group to a simulator not in that group), the corresponding part of the time is cut off.
This results in the simulator outside the group not seeing the steps inside the group.
It therefore only considers the steps of its inputs done when the simulators in the group progress their actual time, i.e. when they conclude their negotiation.

Similarly, a time entering a group will be padded with zeros at the end.

To force users to update their simulations (so they don't silently start producing completely different results), we decided to outlaw weak connections outside of groups.
A user using weak connections will receive an error message leading them to the documentation that explains how to adapt their scenario.

The category of tiered intervals
--------------------------------

This is additional mathematical information on tiered time.

Times are used in two different ways:
They can represent specific points in the simulation or they can represent intervals of time.
Previously, both of these concepts were represented by the same data structure internally.
With tiered time, we also introduce *tiered interval*, so tiered times now only represent points in time.
It is legal to add an interval to a time, and to add two intervals, but it is not legal to add two times.

Speaking of intervals, there are three basic types:

- Connections within a group keep the number of tiers fixed an just add something to some tiers (usually nothing at all, or 1 to the first tier for time-shifted connections, or 1 to the last tier for weak connections).
- Connections leaving a group cut off some tiers at the end.
- Connections entering a group add some tiers at the end.

When calculating the progression within the simulation, it becomes necessary to add these types of intervals together, leading to mixed types.
Therefore, a tiered interval consists of:

- A list of addition tiers.
  These are added to the corresponding tiers of the tiered time.
  All further tiers of the tiered time are cut off.
- A list of extension tiers.
  There are appended to the result of the addition and cutoff.
- A pre-length, which is used as a sanity check.
  The pre-length must equal the number of tiers of the time to which the interval is added.
  Also, the pre-length serves as an upper bound for the number of addition tiers, so that the time always has enough components to add to.

The addition rules for intervals are set up such that adding two intervals to a time one after the other is the same as adding the sum of the two intervals to the time, and such that the addition of intervals is associative.
(Mathematically, this turns tiered times and intervals into a category with sets of tiered times of the same length as objects and tiered intervals as arrows.)