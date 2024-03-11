.. _demo2:

Integrating a control mechanism
===============================

The scenario that we're going to create in this part of the tutorial will
be similar to the one we created before but incorporate the control mechanism
that we just created.

Again, we start by setting some configuration values and creating a simulation
world:

.. literalinclude:: code/demo_2.py
   :end-before: End: Create World

We added *ExampleCtrl* to the sim config and let it be executed in-process
with mosaik.

We can now start one instance of each simulator:

.. literalinclude:: code/demo_2.py
   :start-at: Start simulators
   :end-before: End: Start simulators

We'll create three model instances, the same number of agents, and one database:

.. literalinclude:: code/demo_2.py
   :start-at: Instantiate models
   :end-before: End: Instantiate models

We use a `list comprehension`__ to create three model instances with individual
initial values (-2, 0 and 2). For instantiating the same number of agent
instances we use ``create()`` which does the same as a list comprehension but
is a bit shorter.

__ https://docs.python.org/3/tutorial/datastructures.html#list-comprehensions

Finally we establish pairwise bi-directional connections between the models
and the agents:

.. literalinclude:: code/demo_2.py
   :start-at: Connect entities
   :end-before: End: Connect entities

The important thing here is the ``weak=True`` argument that we pass to the
second connection. This tells mosaik how to resolve the cyclic dependency, i.e.
which simulator should be stepped first in case that both simulators have a
scheduled step at the same time. (In our example this will not happen, as the
agents are only stepped by the models' outputs.)

Finally, we can connect the models and the agents to the monitor and run the simulation:

.. literalinclude:: code/demo_2.py
   :start-at: Connect to monitor

In the printed output of the collector, you can see two important things: The
first is that the agents only provide output when the delta of the controlled
model is to be changed. And second, that the new delta is set at the models'
subsequent step after it has been derived by the agents.

.. literalinclude:: code/demo_2.out

This is the complete scenario:

.. literalinclude:: code/demo_2.py

Congratulations, you have mastered the mosaik tutorial. The following sections
provide a more detailed description of everything you learned so far.
