===================================
Scheduling and simulation execution
===================================

When you :doc:`defined your scenario <scenario-definition>` and :ref:`start the
simulation <running-the-simulation>`, mosaik's scheduler becomes active. It
manages the execution of all involved simulators, keeps them in sync and
handles the :term:`data-flows <data-flow>` between them.

Mosaik runs the simulation by :term:`stepping <step>` simulators through time.
The time has internally no unit attached, but by convention, seconds are used.
If all simulators involved in your scenario agree on another unit (e.g.,
minutes or milliseconds), this can be used as well.


Anatomy of a step
=================

When the simulation starts, all simulators are at time 0. Mosaik tracks the
current simulation time for every simulator individually. When it asks
a simulator to perform its next step, it passes its current simulation time
*t*:sub:`now` to it. After its step, the simulator returns the time at which it
wants to perform its next step (*t*:sub:`next`). Thus, a simulator's step size
doesn't need to be constant but can vary during the simulation.

The data that a simulator computes during a step is valid for the right-open
interval [*t*:sub:`now`, *t*:sub:`next`) as shown in the following figure.


.. figure:: /_static/scheduler-step.*
   :width: 600
   :align: center
   :alt: Anatomy of a step

   Schematic execution of a simulator *A*. *t*:sub:`now`, *t*:sub:`next` and
   the validity interval for its first step 0 are shown. The figure also shows
   that the step size of a simulator may vary during the simulation.


Synchronization and data-flows
==============================

If there are data-flows between two simulators (because you connected some of
their entities), a simulator can only perform a step if all input data has been
computed.

Let's assume we created a data-flow from a simulator *A* to a simulator *B* and
*B* wants to perform a step from *t*:sub:`now(B)`. Mosaik determines which
simulators provide input data for *B*. This is only *A* in this example. In
order to provide data for *B*, *A* needs to step far enough to produce data for
*t*:sub:`now(B)`, that means *t*:sub:`next(A)` > *t*:sub:`now(B)` as the
following figure illustrates.

.. figure:: /_static/scheduler-step-dependencies.*
   :width: 600
   :align: center
   :alt: t_next(A) must be greater then t_now(B) in order for B to step.

   **(a)** *B* cannot yet step because *A* has not progressed far enough yet
   (*t*:sub:`next(A)` <= *t*:sub:`now(B)`).

   **(b)** *B* can perform its next step, because *A* now has progressed far
   enough (*t*:sub:`next(A)` > *t*:sub:`now(B)`).

If this condition is met for all simulators providing input for *B*, mosaik
collects all input data for *B* that is valid at *t*:sub:`now(B)` (you could
say it takes *one* snapshot of the global simulation state). It passes
this data to *B*. Based upon this (and *only* this) data, *B* performs its step
[*t*:sub:`now(B)`, *t*:sub:`next(B)`).

This is relatively easy to understand if *A* and *B* have the same step size,
as the following figures shows:

.. figure:: /_static/scheduler-dataflow-1-1.*
   :width: 600
   :align: center
   :alt: Dataflow from A to B where both simulators have the same step size.

   In this example, *A* and *B* have the same step size. Mosaik steps them
   in an alternating order starting with *A*, because it provides the input
   data for *B*.

If *B* had a larger step size then *A*, *A* would produce new data while *B*
steps. *B* would still only use the data that was valid at *t*:sub:`now(B)`,
because it only "measures" its inputs once at the beginning of its step:

.. figure:: /_static/scheduler-dataflow-1-2.*
   :width: 600
   :align: center
   :alt: Dataflow from A to B where B has a larger step size.

   In this example, *B* has a larger step size. It doesn't consume all data
   that *A* produces, because it only gets data once at the beginning of its
   step.

On the other hand, if *A* had a larger step size then *B*, we would reuse the
same data from *A* multiple times as long as it is valid:

.. figure:: /_static/scheduler-dataflow-2-1.*
   :width: 600
   :align: center
   :alt: Dataflow from A to B where A has a larger step size.

   In this example, *A* has a larger step size. *B* reuses the same data
   multiple times because it is still valid.

The last two examples may look like special cases, but they actually arise from
the approach explained above.


How data flows through mosaik
-----------------------------

After a simulator is done with its step, mosaik determines, based on the
data-flows that you created in your scenario, which data other simulators need
from it. It makes a *get_data()* API call to the simulator and stores the data
that this call returns in an internal buffer. It also memorizes for which
period of time this data is valid.

Before a simulator steps, mosaik determines in a similar fashion what input
data the simulator needs. Mosaik checks its internal data buffer if input data
from all simulators is available. If not, it waits until all simulators stepped
far enough to provide that data. All input data is then passed to the *inputs*
parameter of the *step()* API call.

It is important to understand that simulators don't talk to each other directly
but that all data flows through mosaik were it can be cached and managed.


Cyclic data-flows
=================

Cyclic data-flows are necessary to model situations in which a control
mechanism *(C)* controls another entity *(E)* based on its state, e.g. by
sending commands or a schedule.

It is not possible to perform both data-flows (the state from *E* to *C* and
the commands/schedule from *C* to *E*) at the same time because they depend on
each other (yes, this is similar to the chicken or egg dilemma).

The cycle can be resolved by first stepping *E* (e.g., from *t* = 0 to *t*
= 1). *E*\ ’s state for that interval can then be used as input for *C*\ ’s
step for the same interval. The commands/schedule that *C* generates for *E*
will then be used in *E*\ ’s next step.

.. figure:: /_static/scheduler-cyclic-dataflow.*
   :width: 600
   :align: center
   :alt: Cyclic data-flow between a controller and a controlled entity.

   In this example, a controlled entity *E* provides state data to the
   controller *C*. The commands or schedule from *C* is used by *E* in its next
   step.

This resolution of the cycle makes sense if you think how this would work in
real life. The controller would measure the data from the controlled unit at
a certain point *t*. It would then do some calculation which take a certain
amount of time Δ\ *t* which would be send to the controlled unit at *t* + Δ\
*t*.

However, mosaik is not able to automatically resolve that cycle. That's why you
are not allowed to ``connect(E, C)`` and ``connect(C, E)`` in a scenario.
Instead you have to ``connect(E, C, async_requests=True)`` and use the
:ref:`asynchronous callback <async_requests_overview>` ``set_data()`` in *C*\
’s *step()* implementation in order to send the commands or schedule from *C*
to *E*.

You can take a look at our :ref:`discussion of design decissions
<circular-data-flows>` to learn why cyclic data-flows are handled this way.


Stepping and simulation duration
================================

By now you should have a general idea of how mosaik handles data-flows between
simulators. You should also have the idea that simulators only perform a step
when all required input data is available. But what if they don't need any? In
this section you'll learn about the algorithm that mosaik uses to determine
whether a simulator can be stepped or not.

The general idea behind idea is laziness. A simulator will only step if it
really needs to. This is usually, because someone else needs its data. This
becomes problematic if your simulator is the only one in the simulation (e.g.,
for testing purposes) or at the end of a data-flow chain.

This is how it works:

1. Should there be a next step at all? :sup:`*`

   *Yes:* Go to step 2.

   *No:* Stop the simulator.

   :sup:`*` *We'll explain how to answer this question below.*

2. Are there simulators that need data from us?

   *Yes:* Go to step 3.

   *No:* Go to step 4.

3. Does a depending simulator require new data from us?

   *Yes:* Go to step 4.

   *No:* Wait until someone does. Then go to step 4.

4. Is all required input data from other simulators available?

   *Yes:* Go to step 5.

   *No:* Wait until all data is available. Then go step 5.

5. Collect all required input data.

6. Send collected input data to simulator, perform the simulation step and get
   the time for the next step.

7. Get all data from the simulator that other simulators need.

8. Notify simulators that already wait for that data.


So how do we determine whether a simulator must perform another step of it is
done?

When we start the simulation, we pass a time unto which our simulation should
run (``world.run(until=END)``). Usually a simulator is done if the time of its
next step is larger then the value of *until*. This is, however, not true for
*all* simulators in a simulation. If no one needs the data of a simulator step,
why perform this step?

So the actual algorithm is as follows:

If a simulator has no outgoing data-flows (no other simulator needs its data)
it simulates until the condition *t*:sub:`next` > *t*:sub:`until` is met.

Else, if a simulator needs to provide data for other simulators, it keeps
running until all of these simulators have stopped.

The algorithm explained above allows mosaik to perform as little simulation
steps as possible and only perform theses steps when necessary.
