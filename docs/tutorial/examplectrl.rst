.. _examplectrl:

Adding a control mechanism to a scenario
========================================

Now that we integrated our first simulator into mosaik and tested it in
a simple scenario, we should a control mechanism and mess around with our
example simulator a little bit.

As you remember, our example models had a *value* to which they added something
in each step. Eventually, their value will end up to be very high. We'll use
a multi-agent system to keep the values of our models in [-3, 3]. The agents
will monitor the current *value* of their respective models and when it reaches
-3/3, they will set *delta* to 1/-1 for their model.

Implementing the Sim API for control strategies is very similar to implementing
it for normal simulators. We start again by importing the :mod:`mosaik_api`
package and defining the simulator meta data:

.. literalinclude:: code/controller.py
   :lines: 1-17

Our control mechanism will use agents to control other entities. The agent has
no parameters and only one attribute for incoming values.

Lets continue and implement :class:`mosaik_api.Simulator`:

.. literalinclude:: code/controller.py
   :lines: 20-23

Again, nothing special is going on here. We pass our meta data dictionary to
our super class and set an empty list for our agents.

Since our agent doesn't have any parameters, we don't need to implement
:meth:`~mosaik_api.Simulator.init()`. The default implementation will return
the meta data, so there's nothing we need to do in this case.

Implementing :meth:`~mosaik_api.Simulator.create()` is also straight forward:

.. literalinclude:: code/controller.py
   :lines: 25-33

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
   :lines: 35-38

The ``commands`` dict will contain the commands that our control mechanism is
going to send to the example simulator. We fill this dict in the following
loop. In that, we iterate over all inputs and extract the input values for each
agent; so ``values`` is a dict containing the current values of all models
connected to that agent, e.g., `values == {'Model_0': 1}`

We now check the every input value:

.. literalinclude:: code/controller.py
   :lines: 39-46

If the value is ≤ -3 or ≥ 3, we have to set a new *delta* value. Else, we don't
need to do anything and can continue with a new iteration of the loop.

If we have a new *delta*, we add it to the ``commands`` dict:

.. literalinclude:: code/controller.py
   :lines: 47-52

After finishing the loop, the ``commands`` dict may look like this:

.. code-block:: python

   {
       'Agent_0': {'Model_0': {'delta': 1}},
       'Agent_2': {'Model_2': {'delta': -1}},
   }

*Agent_0* sets for *Model_0* the new *delta* = 1. *Agent_2* sets for *Model_2*
the new *delta* = -1. *Agent_1* did not set a new *delta*.

So now that we create all commands – how do they get to the example simulator?
The way via :meth:`~mosaik_api.Simulator.get_data()` is not possible since it
would require a circular data-flow like ``connect(model, agent); connect(agent,
model)`` which mosaik cannot resolve (You can read :ref:`the details
<circular-data-flows>` if you are curious why).

Instead, we use one of the :ref:`asynchronous requests
<async_requests_overview>` that you can perform within
:meth:`~mosaik_api.Simulator.step()`, namely
:meth:`~mosaik.simmanager.MosaikRemote.set_data()`. The
:class:`~mosaik_api.Simulator` makes these requests available via the
:attr:`~mosaik_api.Simulator.mosaik` attribute:

.. literalinclude:: code/controller.py
   :lines: 53-56

The :meth:`~mosaik.simmanager.MosaikRemote.set_data()` actively sends the
commands to mosaik which will pass them to the example simulator in its next
step.

.. note::

   *yield???* If you are new to Python and don't know what the ``yield``
   keyword does: Don't worry! In this case, it will just block the execution of
   ``step()`` until all commands are sent to mosaik. After that, the method
   will normally continue its execution.

When all commands are sent to mosaik, we are done with our step and return the
time for our next one (which should be in one minute).

That's it. Since there's no data to be retrieved, we don't need to implement
:meth:`~mosaik_api.Simulator.get_data()`. The default implementation will raise
an error for us if it should be called accidentally.

Here is the complete code for our (very simple) controller / mutli-agent
system:

.. literalinclude:: code/controller.py

Next, we'll create a new scenario to test our controller.
