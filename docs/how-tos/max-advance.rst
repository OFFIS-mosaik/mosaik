========================================================================
How to avoid unnecessary simulator steps using the ``max_advance`` value
========================================================================

.. currentmodule:: mosaik_api_v3

Event-based simulators frequently have to deal with the following challenge:
They receive input at time :math:`t_1` which triggers a step.
Now they can start calculating, which would result in them producing an event at time :math:`t_2` themselves.
However, if additional input arrives *before* :math:`t_2`, the event at time :math:`t_2` could be affected (e.g., delayed or changed).
As mosaik simulators cannot take back events they have already sent, this puts the simulator in a bind, as it does not know how far it can advance its internal time.

The naive solution to this problem would be to simply always step by the smallest step possible (one time step, in mosaik).
However, when events are actually quite rare, this produces lots of unnecessary steps.

Therefore, mosaik simulators get an additional input to their :meth:`~Simulator.step` methods: the ``max_advance``.
This value indicates to the simulator the earliest time at which it *could* be called again if

- It does not schedule a step for itself for an earlier time.
- It does not send out events of its own at earlier times (as these could lead to unforseen feedback loops that result in earlier steps after all).

Essentially, mosaik looks at all steps in the system of which it knows, and calculates the shortest path by which one of these steps could trigger the simulator in question.


How to use ``max_advance`` in practice
======================================

If your simulator could benefit from ``max_advance``, here is how to use it:
When you are stepped at some time :math:`t_1`, start advancing your internal model until either:

- you have reached ``max_advance`` or
- your model produces an event at time :math:`:t_2` that you pass out to mosaik.

If you produce events, pass them out to mosaik in :meth:`~Simulator.get_data` using the possibility to specify :math:`t_2` as the time for that output.
(You do this by adding a *time* field to your output dictionary.)
If your simulator needs to advanced further afterwards (because it is not guaranteed that it won't produce further events without further input, or because it is the most convenient way of using your simulation model), also return time :math:`t_2` from :meth:`~Simulator.step` as the next time where you want to be stepped.
Otherwise, you can just return `None`; if further external events reach it, it will be woken up again.


Example of using ``max_advance``
================================

In this example, we will consider a countdown simulator.
It has an internal value ``c`` which starts at some value is reduced by 1 in each mosaik step.
When the value reaches 2, a *Warning* event is emitted.
When the value reaches 0, a *ZeroReached* event is emitted.
(Both don't carry extra information.)
Additionally, the simulator accepts a *Set* event, which sets ``c`` to the value transmitted with that event.

A naive implementation would step this simulator with a time increment of 1.
At each step, the simulator's internal value would be set to the *Set* value if provided, and decremented by 1 otherwise.
If one of the two thresholds were reached, the corresponding *Warning* or *ZeroReached* event would be emitted.

However, this is inefficient (unless *Set* events are very frequent), as the time of the next *Warning* or *ZeroReached* can be predicted, provided no *Set* occurs before then.
This is where ``max_advance`` helps.

Let's say the simulator starts at time 0 with ``c = 10`` and gets called with a ``max_advance`` of 4.
We currently expect that the *Warning* event will occur at time 8.
However, because this is later than ``max_advance``, we do not emit this event yet.
Rather, we decrease our timer by 5 and request to be called at time 5 again (the earliest time at which new data might arrive).

Let's now say that we do get a *Set* event at time 5 with value 3, and another ``max_advance`` 4 steps in the future, i.e. ``max_advance = 9``.
We can now see that it would have been wrong to emit a *Warning* event for time 8:
With the new value of ``c``, we reach our *Warning* threshold earlier, namely in one more step at time at 6.
This time, the predicted event time for that *Warning* is not later than ``max_advance``, so we can safely emit it.
That is, we return a *Warning* event at ``time = 6``.

We also request to be called again at time 6 because we currently predict that we will also have to emit *ZeroReached* at time 8.
Even though 8 also lies before ``max_advance``, we cannot emit the *ZeroReached* event yet:
Because we emit an event at time 6, the rest of the simulation will get a chance to react, and this might result in events earlier than ``max_advance``.

Let's say our warning works, and some other simulation component reacts by sending us a new *Set* event at time 7 with a value of 5.
This means that we will not reach 0 by time 8 as previously predicted, so it is a good thing that we didn't emit that event yet.

This event at time 7 will likely (though not definitively) come with the same ``max_advance`` of 9, so let's also assume that in this example.
With the new value of ``c``, we predict a new *Warning* at time 10.
As this lies after ``max_advance`` we don't emit it yet, instead requesting a new call at time 10 (and decreasing ``c`` to 2).

Finally, let's assume that we do not get a new *Set* event at that time, and that ``max_advance`` is 14 now.
So at time 10, we emit our *Warning*, and ask to be called at 10 a second time.
This time, let's assume that the rest of the simulation does not react to the warning.
In this case, we would be called again at time 10 with ``max_advance = 14`` and no event.
Now we can safely emit ``ZeroReached`` at time 12.
This time, we do not need to request another step for ourselves, as ``c`` will just keep decreasing and never pass 2 or 0 again.
This can only change if we receive a *Set* event with a non-negative value, in which case we will be called regardless.

The following graph illustrates the value of ``c`` and the events that occurred:

The following code implements this simple simulator.
A real implementation should support creating multiple *Countdown* entities, but this would complicate the implementation:
