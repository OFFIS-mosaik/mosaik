===============
Troubleshooting
===============

This is a collection of difficulties users have experienced with mosaik, and of solutions to them.
The list is still (very) short.
If you run into a problem not resolved here, please let us know on our `GitHub discussions <https://github.com/orgs/OFFIS-mosaik/discussions>`_, regardless of the level of question.
This way, we can hopefully turn this page into a useful resource for all users.


mosaik raises an exception
==========================

mosaik has fine-grained exception classes for most things that can go wrong in a mosaik simulation.
If you run into an exception, you should first head to the :doc:`documentation of the exceptions module </api_reference/mosaik.exceptions>` and find your exception there.
This might already contain some more hints on how to proceed.

Otherwise, you should check the exception's base class listed there.
If it is :exc:`~mosaik.exceptions.ScenarioError`, this indicated a mistake in your scenario, which you almost certainly need to fix yourself.
If it is :exc:`~mosaik.exceptions.SimulatorError`, this is an error in a simulator, and it's usually the simulator author's responsibility to fix it (though in rare cases it might be an issue of you using the simulator incorrectly).
Finally, if it is :exc:`~mosaik.exceptions.SimulationError`, the error might lie both with you or the simulator author.

In any case, if you get stuck, feel free to ask on our `GitHub discussions`_.


The ``finalize`` methods of connected simulators don't get called
=================================================================

This happens if the ``world`` in your scenario never gets shut down.

We recommend using the ``world`` with a ``with`` block like so::

   with mosaik.World(SIM_CONFIG) as world:
       # your scenario script here
       ...

       world.run(until=UNTIL)

Or, for async scenarios::

   async with mosaik.AsyncWorld(SIM_CONFIG) as world:
       # your scenario setup here
       ...

       world.run(until=UNTIL)

This will reliably call :meth:`World.shutdown <mosaik.scenario.World.shutdown>` or :meth:`AsyncWorld.shutdown <mosaik.async_scenario.AsyncWorld.shutdown>`, even in the case of exceptions.

If using a ``with`` block is not feasible for you, the non-async world's :meth:`~mosaik.scenario.World.run` method will also call ``shutdown`` for you if no exception occurs.
In case of exceptions and for :class:`~mosaik.async_scenario.AsyncWorld`, you need to call ``world.shutdown()`` manually.
