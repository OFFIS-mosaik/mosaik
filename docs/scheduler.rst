===================================
Scheduling and simulation execution
===================================

When you :doc:`defined your scenario <scenario-definition>` and :ref:`start the
simulation <running-the-simulation>`, mosaik's scheduler becomes active. It
manages the execution of all involved simulators, keeps them in sync and
handles the :term:`data-flows <data-flow>` between them.

Mosaik runs the simulation by :term:`stepping <step>` simulators through time.
Mosaik uses integers for the representation of time (to avoid rounding errors
etc.). It's unit (to how many seconds one integer step corresponds) can be
defined in the scenario, and is passed to every simulation component via the
:ref:`init function <api.init>` as key-word parameter *time_resolution*. It's
a floating point number and defaults to *1.*.


.. _time_paradigms:

Time paradigms
==============

There are various paradigms for time in simulations, discrete time, continuous
time, discrete event, to name the probably most common ones. Mosaik supports
discrete-time and discrete-event simulations, including the combination of both.
As these concepts are not always strictly distinguishable, we use a slightly
different notation for the simulator's types, namely time-based, event-based,
and hybrid. It's not always obvious which type of simulator is the most
appropriate one for a simulator, and in many cases both would be possible. As
a rough guide we could say:

Time-based simulators are more related to the physical world,
where the state, inputs and outputs of a system are continuous (e.g. active
power of a PV module). The mapping of those continuous signals to discrete
points in time is then somewhat arbitrary (and depends on the desired precision
and the available computing resources). The lower limit for the temporal
resolution in a mosaik scenario is the unit assigned to the integer time steps.

Event-based simulators are related to the cyber world, where the state(s)
of a system can instantaneously change, and inputs and outputs also occur at
a specific point in time (example: sending/receiving of messages in a
communication simulation). The native way of stepping through time would than
be to just jump between all occurring events. In a mosaik simulation the time
of the events have to be rounded to the mosaik's integer time steps.

Hybrid simulators can represent any kind of combined systems with both
continuous and event-type components.


.. _stepping_types:

Advancing through time
======================

Mosaik tracks the current simulation time for every simulator individually. How
simulators step through the time from simulation start to end depends on their
stepping type described above:

Time-based simulators
---------------------

When the simulation starts, all time-based (and hybrid) simulators are at time 0.  When it asks
a simulator to perform its next step, it passes its current simulation time
*t*:sub:`now` to it. After its step, the simulator returns the time at which it
wants to perform its next step (*t*:sub:`next`). Thus, a simulator's step size
doesn't need to be constant but can vary during the simulation.

All data that a time-based simulator computes during a step is valid for the right-open
interval [*t*:sub:`now`, *t*:sub:`next`) as shown in the following figure.


.. figure:: /_static/scheduler-step.*
   :width: 600
   :align: center
   :alt: Time-based scheduling

   Schematic execution of a time-based simulator *A*. *t*:sub:`now`, *t*:sub:`next` and
   the validity interval for its first step 0 are shown. The figure also shows
   that the step size of a simulator may vary during the simulation.

Event-based simulators
----------------------

The stepping through time of event-based simulators is rather different.
Event-based simulators are stepped at all times an event is created at. These
events can either be created by other simulators w are connected to this
simulator via providing the connected attribute, or the simulator can also
schedule events for itself via the step function's return value.
The output provided by event-based simulators is only valid for a specific
point in time, by default for the current time of the step, or for any later
time if explicitly set via the (optional) output time. Providing the output
attributes is optional for event-based simulators. As consequence a simulator
connected to a specific attribute is only triggered/stepped if the output is
actually provided. See the :ref:`API description <api.get_data>` for
implementation details.
Event-based simulators do not necessarily start at time 0, but whenever their
first event is scheduled, either by other simulators or via
:meth:`World.set_initial_event()` from the scenario definition.

.. figure:: /_static/scheduler-event-based-1.*
   :width: 600
   :align: center
   :alt: Event-based scheduling

   Schematic execution of an event-based simulation. Depending on *A*'s
   actual output a step of *B* is triggered (or not), at *A*'s step time or
   later. Simulator *A* also schedules itself.

Note that it is possible that a simulator is stepped several times at a
specific point in time. See :ref:`Same-time loops <same-time_loops>` for details.


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


.. _max_advance:

How far is a simulator allowed to advance its time?
---------------------------------------------------

As described in the :ref:`API documentation <api.step>`, mosaik tells the
simulator each step how far it is allowed to advance its internal simulation
time via the *max_advance* argument. It is guaranteed that no step will be
scheduled until then (inclusively), unless the simulator activates a
triggering dependency loop earlier than that.
Mosaik deduces this from the simulation topology and the progress of the
simulators. Note that the simulator will not necessarily be stepped at
`max_advance + 1` as this will only happen if the predecessor actually
provides the connected output attribute(s).

As time-based simulators (or hybrid ones without any triggering input) only
decide themselves when they are stepped, max_advance is always equal to the
end of the simulation for those. But of course they will most likely miss some
updates of the input data if their step size is too large and not synchronized
with their input providers. In order not to miss any input update, you can
change the type of the simulator to *hybrid*. Then the simulator will be
stepped on each update.

TODO: Add info for rt-simulations


How data flows through mosaik
-----------------------------

After a simulator is done with its step, mosaik determines, based on the
data-flows that you created in your scenario, which data other simulators need
from it. It makes a *get_data()* API call to the simulator and stores the data
that this call returns in an internal buffer. It also memorizes for which
time this data is valid.

Before a simulator steps, mosaik determines in a similar fashion what input
data the simulator needs. Mosaik checks if all input-providing simulators have
stepped far enough to (potentially) provide that data and waits otherwise.
After that all input data is collected and then passed to the *inputs*
parameter of the *step()* API call.

It is important to understand that simulators don't talk to each other directly
but that all data flows through mosaik were it can be cached and managed.


Cyclic data-flows
=================

Sometimes the simulated system requires cyclic data-flows between components, e.g. a control
mechanism *(C)* that controls another entity *(E)* based on its state, e.g. by sending commands
or a schedule.

It is not possible to perform both data-flows (the state from *E* to *C* and
the commands/schedule from *C* to *E*) at the same time because they depend on
each other (yes, this is similar to the chicken or egg dilemma).

The cycle can be resolved by first stepping *E* (e.g., from *t* = 0 to *t*
= 1). *E*\ ’s state for that interval can then be used as input for *C*\ ’s
step for the same interval. The commands/schedule that *C* generates for *E*
will then be used in *E*\ ’s next step. This results in a serial execution,
also called Gauss-Seidel scheme.

.. figure:: /_static/scheduler-cyclic-dataflow-sequential.*
   :width: 600
   :align: center
   :alt: Serial cyclic data-flow between, e.g. between a controller and a controlled entity.

   In this example, a controlled entity *E* provides state data to the
   controller *C*. The commands or schedule from *C* is used by *E* in its next
   step.

This resolution of the cycle makes sense if you think how this would work in
real life. The controller would measure the data from the controlled unit at
a certain point *t*. It would then do some calculation which take a certain
amount of time Δ\ *t* which would be send to the controlled unit at *t* + Δ\
*t*.

However, mosaik is not able to automatically resolve that cycle. That's why you
are not allowed to ``connect(E, C)`` and ``connect(C, E)`` in a scenario. This can be done
via the time-shifted connection
``connect(C, E, (‘c_out’, ‘a_in’), time_shifted=True, initial_data={‘c_out’: 0})``,
which tells mosaik that the output of *C* is to be used for E's next time step(s) afterwards.
As for the first step (at time 0) this data cannot be provided yet, you have to set it via the
initial_data argument. In this case, the initial data for *‘a_in’* is 0.

Another way to resolve this cycle is to allow async. requests via the async_requests flag
``connect(E, C, async_requests=True)`` and use the
:ref:`asynchronous callback <async_requests_overview>` ``set_data()`` in *C*\
’s *step()* implementation in order to send the commands or schedule from *C*
to *E*. The advantage of this approach is that the call of set_data is optional, i.e. the commands
or schedules don't need to be sent on every step.


If you set the time_shifted flag for both connections, the simulators can be
executed in parallel (Jacobi scheme). Note that a computationally parallel
execution is only possible for simulators that are not run in-process.

.. figure:: /_static/scheduler-cyclic-dataflow-parallel.*
   :width: 600
   :align: center
   :alt: Parallel cyclic data-flow.

   In this example, two entities are running in parallel. The outputs of each
   simulator are used by the other one in its next step afterwards.

You can take a look at our :ref:`discussion of design decisions
<circular-data-flows>` for details.


.. _same-time_loops:

Same-time (algebraic) loops
---------------------------

Loops which are closed by a weak connection can be run multiple times within
the same mosaik time step, as weak connections do not necessarily imply a
temporal. This can be used for example to only advance the simulation time
when the state has converged to a stable solution. To activate (and also stay
in) a same-time cycle, a simulator has to provide its 'cyclic' attribute(s) via
the :ref:`api.get_data` function and indicating as output time the current
step time. To omit the cycle the attribute(s) in the get_data's return
dictionary or indicating a time later than the step's time.

.. figure:: /_static/scheduler-event-based-2.*
   :width: 300
   :align: center
   :alt: Same-time loops

   A same-time loop with three repetitions between simulator *A* and *B*.

To prevent the loop to be run infinite times, mosaik raises a runtime error
when a certain number of iterations within one time step has been reached. The
default maximum iteration count is 100 and can be adjusted via the
*max_loop_iterations* parameter within the scenario definition if needed (see
:class:`mosaik.scenario.World`).


Stepping and simulation duration
================================

By now you should have a general idea of how mosaik handles data-flows between
simulators. You should also have the idea that simulators only perform a step
when all input-providing simulators have stepped far enough. But what if they
don't have any (connected) inputs? In this section you'll learn about the
algorithm that mosaik uses to determine whether a simulator can be stepped or
not.


.. figure:: /_static/sim_process.*
   :width: 300
   :align: center
   :alt: Simulator process

   Sim-process running for each simulator in parallel

This is how it works:

1. Should there be a next step at all? :sup:`*`

   *Yes:* Go to step 2.

   *No:* Stop the simulator.

   :sup:`*` *We'll explain how to answer this question below.*

2. Is a next step already scheduled, either self-scheduled via step or
by triggering input?

   *Yes:* Go to step 3.

   *No:* Wait until a next step is set. Then go to step 3.

3. Have all dependent simulators stepped far enough?

   *Yes:* Go to step 4.

   *No:* Wait for all dependencies. Then go step 4.

4. Collect all required input data.

5. Send collected input data to simulator, perform the simulation step and
   eventually get the time of a next step.

6. Get all data from this simulator that are connected to other simulators and
   store it internally.

7. Notify other simulators that already wait for this simulator. If there's
   any output which is connected to a triggering input of another simulator,
   schedule new steps for it (at output time).


So how do we determine whether a simulator must perform another step or it is
done?

When we start the simulation, we pass a time unto which our simulation should
run (``world.run(until=END)``). Usually a simulator is done if the time of its
next step is equal or larger then the value of *until*. This is, however, not
true for *all* simulators in a simulation. If no one needs the data of a
simulator step, why perform this step?

So the actual algorithm is as follows:

If a simulator has no outgoing data-flows (no other simulator needs its data)
it simulates until the condition *t*:sub:`next` > *t*:sub:`until` is met or
none of the simulators which could trigger a step are running anymore.

Else, if a simulator needs to provide data for other simulators, it keeps
running until all of these simulators have stopped.
