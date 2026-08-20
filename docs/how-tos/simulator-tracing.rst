============================
How to trace simulator calls
============================

Simulator call traces help explain the interactions in a scenario.
They show calls in both directions, including arguments, return values,
and exceptions. Traces bind the simulator name to the ``simulator`` field:

* ``sim.local.<sim_id>`` for in-process simulators
* ``sim.remote.<sim_id>`` for networked simulators

The traces are emitted at loguru's ``TRACE`` level. Enable mosaik's
logging, then select the desired namespace using a sink filter::

    import sys
    from loguru import logger

    logger.enable("mosaik")
    simulator_filter = "sim.local.Input"
    logger.add(
        sys.stderr,
        level="TRACE",
        filter=lambda record: record["extra"]
        .get("simulator", "")
        .startswith(simulator_filter),
        format="{level: <8} | {extra[simulator]} | {message}",
    )

The filter can be ``sim`` for all simulators, ``sim.local`` or
``sim.remote`` for one transport type, or the full name of a specific
simulator.

Example scenario
----------------

This scenario connects a constant input to an output collector and
only displays traces for the simulator with the ID ``Input``:

.. literalinclude:: code/simulator_tracing.py
   :language: python

Representative output
---------------------

Some large return values are abbreviated here. The scenario itself
prints them in full::

    TRACE    | sim.local.Input | mosaik -> simulator: init('Input', time_resolution=1.0, step_size=1)
    TRACE    | sim.local.Input | simulator -> mosaik: init returned {...}
    TRACE    | sim.local.Input | mosaik -> simulator: create(1, 'Constant', constant=42)
    TRACE    | sim.local.Input | simulator -> mosaik: create returned [{'eid': 'Constant-0', 'type': 'Constant'}]
    TRACE    | sim.local.Input | mosaik -> simulator: step(0, {}, 2)
    TRACE    | sim.local.Input | simulator -> mosaik: step returned 1

The arrows indicate whether the call or response is travelling from
mosaik to the simulator or from the simulator back to mosaik.
