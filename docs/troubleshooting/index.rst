===============
Troubleshooting
===============

This is a collection of difficulties users have experienced with mosaik, and of solutions to them.
The list is still (very) short.
If you run into a problem not resolved here, please let us know on our `GitHub discussions <https://github.com/orgs/OFFIS-mosaik/discussions>`_, regardless of the level of question.
This way, we can hopefully turn this page into a useful resource for all users.


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
