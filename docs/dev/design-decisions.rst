==============================
Discussion of design decisions
==============================

On this page, we discuss some of the design decisions that we made. This should
explain why some features are (not) present and why they work the way that they
work.

.. note::

   For the sake of readability, some concepts are simplified in the following
   sections. For example, the snippet ``connect(A, B)`` means we'e connecting
   some entities of a simulator *A* to some entities of simulator *B*;
   *simulator* and *entity* are used as if they were the same concept;
   *A.step()* means, that mosaik calls the *step()* function of
   simulator/entity *A*.


.. _circular-data-flows:

Circular data-flows
===================

Circular data-flows were one of the harder problems to solve.

When you connect the entities of two simulators with each other, mosaik tracks
the new dependency between these simulators:

.. code-block:: python

   connect(A, B)

*A* would now provide input data for *B*. When mosaik runs the simulation, the
step for a certain time *t* would first be computed for *A* and then for *B*
with the inputs of *A*.

In order to connect control strategies (like multi-agent systems) with
to-be-controlled entities, you usually need a circular data-flow. The entity
provides state information for the controller which in turn sends new commands
or schedules to the controlled entity. The naïve way of doing this would be:

.. code-block:: python

   connect(A, B, 'state')
   connect(B, A, 'schedule')

*A* would receive schedules via the inputs of *A.step()*. In *A.step()*, it
would compute new state information which mosaik would get via *A.get_data()*.
Mosaik would forward this to the inputs of *B.step()*. *B.step()* would
calculate some schedules, which mosaik would again get via *B.get_data()* and
pass to *A.step()* …

The question that arise here is: Which simulator do we step first – *A* or *B*?
Mosaik has no clue.  You *could* say that *A* needs to step first, because the
data-flow from *A* to *B* was established first. However, if you re-arrange
your code and (accidentally) flip both lines, you would get a different
behavior and a very hard to find bug.

What do we learn from that? We need to explicitly tell mosaik how to resolve
these cycles and prohibit normal circular data-flows as in the snippet above.

If you remember mosaik 1, your next approach would be as follows:

.. code-block:: python

   connect(A, B, 'state')
   connect(B, A, 'schedule', delay=True)

This would tell mosaik how to resolve the cycle and throw an error if you
accidentally flip both lines.

Theoretically, we could be done here. But we aren't. The data-flows in the
example above are passive, meaning that *A* and *B* compute data hoping that
someone will use them. This abstraction works reasonably well for normal
simulation models, but control mechanism usually have an *active* roll. They
actively decide whether or not to send commands to the entities they control.

Accordingly, mosaik provides ways for control mechanisms and monitoring tools
to actively collect more data from the simulation and set data to other
entities. These means are implemented as :ref:`asyncronous requests
<async_requests_overview>` that a simulator can perform during its step.
Similar to the cyclic data-flows, this requires you to tell mosaik about it to
prevent some scheduling problems:

.. code-block:: python

   connect(A, B, async_requests=True)

This prevents *A* from stepping too far into the future so that *B* can get
additional data from or set new data to *A* in *B.step()*.

Since you can set data via an asynchronous request, you can implement cyclic
data-flows with it:

.. code-block:: python

   connect(A, B, 'state', async_requests=True)

The implementation of *A.step()* and *A.get_data()* would be the same. In
*B.step()* you would still receive the state information from *A* and compute
the schedules. However, you wouldn't store them somewhere so that
*B.get_data()* can return them. Instead, you would just pass them actively to
*set_data()*. Mosaik stores that data in the same buffer in which it would
store data that it retrieved via *B.get_data()*.

So to wrap this up, there would be two possibilities to achieve cyclic
data-flows:

1. Passive controller:

   .. code-block:: python

      connect(A, B, 'state')
      connect(B, A, 'schedules', delay=True)

   *B.step()* computes schedules and caches them somewhere. Mosaik gets these
   schedules via *B.get_data()* and sends them to *A*.

   If you forget to set the ``delay=True`` flag, mosaik will raise an error at
   *composition time*.

   If you forget the second *connect()*, nothing will happen with the
   schedules. You may not notice this for a while.

2. Active controller:

   .. code-block:: python

      connect(A, B, 'state', async_requests=True)

   *B.step()* computes schedules and immediately passes them to *set_data()*.
   Mosaik sends them to *A*.

   If you forget to set the ``async_requests=True`` flag, mosaik will raise an
   error at *simulation time*.

So, two ways to achieve basically the same thing. What does the `Zen of Python
<http://legacy.python.org/dev/peps/pep-0020/>`_ say to this?

   *"There should be one-- and preferably only one --obvious way to do it."*

Since the asynchronous requests can be used for other purposes as well and
thus, cannot simply be stripped away, we chose the second way and excluded the
first possibility.
