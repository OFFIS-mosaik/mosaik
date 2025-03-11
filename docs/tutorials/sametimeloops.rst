========================================
How to simulate at different time scales
========================================

When your co-simulation involves a simulated communication layer, you will potentially run into the following challenge:
Your "main" simulation progresses at a leisurely pace (say in 15-minute intervals).
However, the communication happens at a much faster scale (with sub-second transmission delays, for example).
To resolve this, you have a couple of options:

- You could exagerate the transmission times (say, 1 second each).
  This way, you can step normally.
  However, you need to be careful not to exagerate too much.
  After all, if you send too many messages, your total communication might take longer than one step of the main simulation.
- You could use realistic simulation times, by reducing the :term:`time resolution` of your simulation.
  In some cases, you might still run into the problem of your communication catching up with the main step size; however, this would model realistic consequences, in this case.
  (Unless it is caused by a programming error, of course.)

In both cases, you potentially find a second challenge, though:
Even simulators that are not involved in the communication might need to know about it to some degree.
Namely, because some simulators communicate, their final valid output is not available at the expected stepping times (say 0 seconds, 900 seconds (= 15 minutes), 1800 seconds, etc.) but only a bit later (for example, at 5 seconds, 907 seconds, 1803 seconds, etc.).
Depending on the simulators in the main part of your simulation, this might be cumbersome.

You could also try to have the simulators run a bit early, but this does not work well for the first step, and it requires you to guess correctly how long the communication will take at most.

Luckily, mosaik offers a third option, that is often a good trade-off:
**Simulator groups** and **weak connections**.
(In the past, we also had **same-time loops** with slightly different semantics.)
This how-to explains what they are and how to use them.


What are simulator groups?
==========================

Simulator groups are sets of some simulators in your simulation.
They can be nested, but not overlap in other ways.

After creating your ``world``, you can create a new simulator group by calling::

    with world.group():
        ...

All the simulators *started* within that ``with`` block will be part of this group.
Once the ``with`` block ends, no more simulators can be added to that group.
mosaik calls other than :meth:`world.start <mosaik.scenario.World.start>` (and its async counterpart if your ``world`` is an :class:`~mosaik.async_scenario.AsyncWorld`) are not affected by whether they're in a group or not.
Finally, to nest groups, simply nest the ``with world.group()`` blocks.

If two simulators were started within the same group (including the case where they belong to different sub-groups), you can use the ``weak`` keyword argument in :meth:`world.connect <mosaik.scenario.World.connect>` and other connection methods.
Usually, you will just set it to ``True``, but occasionally, you will also use integer values for finer control.
Data-flow cycles within a simulator group are permissible as long as at least one connection in each cycle is marked as weak.

When simulating such weak cycles, mosaik will not advance the main time of the simulators.
Instead, a hidden, second "tier" of time will be advanced.
Only once the simulators in the group proceed to the next main step will this trigger steps of connected simulators outside of the group.
These simulators will receive the latest outputs of the simulators in the group.
They will not see all the sub-steps taken within the group.

(When you nest groups, each nested group will receive yet an additional tier of time, and steps of this sub-group will not be visible to the containing group.)


How to use simulator groups in practice
=======================================

To effectively make use of simulator groups, you need to first identify the different timescales of your simulation that you want to separate.
In energy system simulations, you will commonly have the a main time progressing in 15-minute steps and a second tier for an information and communication technology (ICT) layer.

In these cases, you will only need one simulator group.
All of the simulators involved in the communications (such as controllers, and assets that report their state to those controllers) will be part of the group.
Simulators that are not directly involved in the communication (such as the power grid simulator) are started outside of the group.

Within the group, some connections need to marked as weak.
Whenever the connection from simulator A to simulator B is marked as weak, simulator B will perform its first sub-step of each main time step without receiving information from simulator A for that time step.
Instead, it will receive the previous main time step's output, if it is persistent, i.e., a measurement.
This allows starting the communication cycle.
(You can also mark both connections as weak, in which case both simulators will start and run in parallel.)

The time synchronization within a group is really quite similar to the time synchronization of mosaik as a whole, except that *weak* is used instead of *time-shifted*.
As simulators cannot return self-steps for the sub-steps, groups also require enough use of events to keep the cycle alive.

This also indicates how a simulator author must prepare their simulator for use within a group:
The simulator must be partially event-based, and it must stop sending events on the the attributes used in the feedback cycles once it is satisfied that the calculation for the current main step has converged.

It is also often a good idea to separate the "final" output to its own attribute.
This way, you can mark it as an event to trigger simulators in the "main" simulation but because it is not part of the cycle, it will not keep it alive.
Alternatively, this final output might also be a measurement if this makes sense for your simulation; in this case, it can be updated throughout the cycle.
