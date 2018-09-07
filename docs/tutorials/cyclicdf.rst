.. _cyclicdf:

.. role::  raw-html(raw)
    :format: html

Cyclic data-flow
================

Sometimes the simulated system requires cyclic data-flows between components
without any control mechanisms involved. In such a case using async_requests
reduces the scenario flexibility since it forces you to specify data exchange
within a simulator’s interface (via *set_data*).

With version 2.5.0 mosaik provides an alternative way to establish cyclic data-flows
between simulators. This is done via time_shifted connections. They are functionally
similar to the async_request concept, but require no adjustment of simulator
interfaces. Furthermore, they can work with cyclic data-flows involving any number
of simulators (not just cyclic interactions between two simulators). As an example,
take three simulators A, B and C that are to be connected in the way A :raw-html:`&rarr;` B, B :raw-html:`&rarr;` C,
C :raw-html:`&rarr;` A. After establishing the first two connections, mosaik will prohibit the third
one since it might lead to deadlocks. It is allowed, however, when established via

.. code-block:: python

    world.connect(src, dest, (‘c_out’, ‘a_in’), time_shifted=True, initial_data={‘c_out’: 0})

This connection will always be handled after all other connections and provide data
to A only for its next time step. This way, deadlocks are avoided. However, input data
for the initial step of A has to be provided. This is done via the initial_data argument.
In this case, the initial data for *‘a_in’* is 0.
