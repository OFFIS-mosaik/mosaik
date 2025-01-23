==============================================================
How to avoid unnecessary simulator steps using ``max_advance``
==============================================================

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


How to use ``max_advance``
==========================

If your simulator could benefit from ``max_advance``, here is how to use it:
When you are stepped at some time :math:`t_1`, start advancing your internal model until either:

- you have reached ``max_advance`` or
- your model produces an event at time :math:`t_2` that you pass out to mosaik.

If you produces events, pass them out to mosaik in ``get_data`` using possibility to specify :math:`t_2` as the time for that output.
If your simulator needs to advanced further afterwards (because it is not guaranteed that it won't produce further events without further input, or because it is the most convenient way of using your simulation model), also return time :math:`t_2` from :meth:`~Simulator.step` as the next time where you want to be stepped.
