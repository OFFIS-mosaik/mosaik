.. _examplectrl:

Adding a control mechanism to a scenario
========================================

Now that we integrated our first simulator into mosaik and tested it in
a simple scenario, we should implement a control mechanism and mess around with our
example simulator a little bit.

As you remember, our example models had a *value* to which they added something
in each step. Eventually, their value will end up being very high. We'll use
a multi-agent system to keep the values of our models in [-3, 3]. The agents
will monitor the current *value* of their respective models and when it reaches
-3/3, they will set *delta* to 1/-1 for their model.

Implementing the Sim API for control strategies is very similar to implementing
it for normal simulators. We start again by importing the :mod:`mosaik_api`
package and defining the simulator meta data:

.. literalinclude:: code/controller.py
   :lines: 1-18

We set the ``type`` of the simulator to 'event-based'. As we have learned, this
has two main implications:

1. Whenever another simulator provides new input for the simulator, a step is
triggered (at the output time). So we don't need to take care of the
synchronisation of the models and agents. As our example simulator is of type
time-based, it is only stepped at its self-defined times and will thus not
be triggered by (potential) outputs of the agents. It will receive any output
of the agents in its subsequent step.

2. The provision of output of event-based simulators is optional. So if there's
nothing to report at a specific step, the attributes can (and should be) omitted
in the get_data's return dictionary.

Our control mechanism will use agents to control other entities. The agent has
no parameters and two attributes, the input 'val_in' and the output 'delta'.

Let's continue and implement :class:`mosaik_api.Simulator`:

.. literalinclude:: code/controller.py
   :lines: 21-24

Again, nothing special is going on here. We pass our meta data dictionary to
our super class and set an empty list for our agents.

Because our agents don't have an internal concept of time, we don't need to take
care of the time_resolution of the scenario. And as there aren't any simulator
parameters either, we don't need to implement
:meth:`~mosaik_api.Simulator.init()`. The default implementation will return
the meta data, so there's nothing we need to do in this case.

Implementing :meth:`~mosaik_api.Simulator.create()` is also straight forward:

.. literalinclude:: code/controller.py
   :lines: 27-35

Every agent gets an ID like "Agent_*<num>*". Because there might be multiple
:meth:`~mosaik_api.Simulator.create()` calls, we need to keep track of how many
agents we already created in order to generate correct entity IDs. We also
create a list of `{'eid': 'Agent_<num>', 'type': 'Agent'}` dictionaries for
mosaik.

You may have noticed that we, in contrast to our example simulator, did not
actually instantiate any *real* simulation models this time. We just pretend to
do it. This okay, since we'll implement the agent's "intelligence" directly in
:meth:`~mosaik_api.Simulator.step()`:

.. literalinclude:: code/controller.py
   :lines: 37-45

The ``inputs`` arguments is a nested dictionary and will look like this:

.. code-block:: python

   {
       'Agent_0': {'val_in': {'ExampleSim-0.Model_0': -1}},
       'Agent_1': {'val_in': {'ExampleSim-0.Model_1': 1}},
       'Agent_2': {'val_in': {'ExampleSim-0.Model_2': 3}}
   }

For each agent, there's a dictionary with all input attributes (in this case
only 'val_in'), containing the source entities (their full_id) with the
corresponding values as key-value pairs.

First we initialize an empty ``data`` dict that will contain the set-points
that our control mechanism is creating for the models of the example simulator.
We'll fill this dict in the following loop. We iterate over all agents and
extract its input 'val_in'; so ``values_dict`` is a dict containing the current
values of all models connected to that agent. In our example we only allow to
connect one model per agent, and fetch its value.

We now do the actual check:

.. literalinclude:: code/controller.py
   :lines: 47-52

If the value is ≤ -3 or ≥ 3, we have to set a new *delta* value. Else, we don't
need to do anything and can continue with a new iteration of the loop.

If we have a new *delta*, we add it to the ``commands`` dict:

.. literalinclude:: code/controller.py
   :lines: 54

After finishing the loop, the ``data`` dict may look like this:

.. code-block:: python

   {
       'Agent_0': {'delta': 1},
       'Agent_2': {'delta': -1},
   }

*Agent_0* sets the new *delta* = 1, and *Agent_2* sets the new *delta* = -1.
*Agent_1* did not set a new *delta*.

At the end of the step, we put the data dict to the class attribute self.data,
to make it accessible in the get_data method

.. literalinclude:: code/controller.py
   :lines: 56

We return *None* to mosaik, as we don't want to step ourself, but only when
the controlled models provide new values.


.. literalinclude:: code/controller.py
   :lines: 58

After having called step, mosaik requests the new set-points via the get_data
function. In principle we could just return the self.data dictionary, as we
already constructed that in the adequate format. For illustrative purposes we
do it manually anyhow. Additionally, if we do it like that, we can only send
back the attributes that are actually needed by (connected to) other
simulators:

.. literalinclude:: code/controller.py
   :lines: 60-72



Here is the complete code for our (very simple) controller / mutli-agent
system:

.. literalinclude:: code/controller.py

Next, we'll create a new scenario to test our controller.
