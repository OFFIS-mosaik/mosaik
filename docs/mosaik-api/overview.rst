========================================
How mosaik communicates with a simulator
========================================

This section provides a general overview which API calls exists and when mosaik
calls them. The following sections will go into more detail.

When the connection between a simulator and mosaik is established, mosaik will
first call ``init()``, optionally passing some global parameters to the
simulator. The simulators returns some meta data describing itself.

Following this, mosaik may call ``create()`` multiple times in order to
instantiate one of the models that the simulator implements. The return value
contains information describing the entities created.

When the simulation has been started, mosaik repeatedly calls ``step()``.  This
allows the simulator to step forward in time. It returns the time at which it
wants to perform its next step.

Finally, mosaik sends a ``stop()`` message to every simulator to request its
shut-down.

The following figure depicts the sequence of these messages:

.. image:: /_static/mosaik-api-sequence.*
   :width: 500
   :align: center
   :alt: Main sequence diagram for the mosaik API.

After ``create()`` or ``step()`` have been called, there may be an
arbitrary amount of ``get_data()`` calls where mosaik requests the current
values of some entities' attributes:

.. image:: /_static/mosaik-api-sequence-get_data.*
   :width: 500
   :align: center
   :alt: Sequence diagram for the get_data() API call.

These methods are usually sufficient to connect simple simulators to mosaik.
However, control strategies, visualizations or database adapters may need to
actively query mosaik for additional data.

.. _async_requests_overview:

Thus, while a simulator is executing a simulation step, it may make
asynchronous requests to mosaik. It can get the current simulation progress
(``get_progress()``), collect information about the simulated topology
(``get_related_entities()``), query other entities for data (``get_data()``)
and set data for other entities (``set_data()``).

.. image:: /_static/mosaik-api-sequence-step.*
   :width: 500
   :align: center
   :alt: Sequence diagram for asychronous requests made by a simulator.

The next two section explain the :ref:`low-level API <low-level-api>` and the
:ref:`Python high-level API <high-level-api>` in more detail.
