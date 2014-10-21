.. _demo2:

Integrating a control mechanism
===============================

The scenario that we're going to create in this last part of the tutorial will
be similar to the one we create before but incorporate the control mechanism
that we just created.

Again, we start by setting some configuration values and creating a simulation
world:

.. literalinclude:: code/demo_2.py
   :lines: 1-21

We added *ExampleCtrl* to the sim config and let all simulators be executed
in-process with mosaik.

We can now start one instance of each simulator:

.. literalinclude:: code/demo_2.py
   :lines: 23-26

We'll create three model instances and one agent, and one database:

.. literalinclude:: code/demo_2.py
   :lines: 28-31

We use a `list comprehension`__ to create three model instances with individual
initial values (-2, 0 and 2). For instantiating the same amount of agent
instances we use ``create()`` which does the same as a list comprehension but
is a bit shorter.

__ https://docs.python.org/3/tutorial/datastructures.html#list-comprehensions

We finally connect each model to an agent (one-to-one):

.. literalinclude:: code/demo_2.py
   :lines: 33-35

The important thing here is the ``async_requests=True`` argument that we pass
to :meth:`~mosaik.scenario.World.connect()`. This tells mosaik that our
control mechanism may do async. requests (e.g., setting data to the models).

Finally, we can connect the models to the monitor and run the simulation:

.. literalinclude:: code/demo_2.py
   :lines: 37-41

In the output, you can clearly see the effect of our control mechanism:

.. literalinclude:: code/demo_2.out
   :lines: 1-10,41-

This is the complete scenario:

.. literalinclude:: code/demo_2.py

Congratulations, you have mastered the mosaik tutorial. The following sections
provide a more detailed description of everything you learned so far.
