.. _examplesim:

.. role::  raw-html(raw)
    :format: html

========================================================
Integrating a simulation model into the mosaik ecosystem
========================================================

In this section we'll first implement a simple example simulator. We'll then
implement mosaik's Sim-API step-by-step.

.. _the_simulator:

The model
=============

We want to implement a very simple model with the following behavior:

- *val*:sub:`0` = *init_val*

- *val*:sub:`i` = *val*:sub:`i − 1` + *delta* for *i* ∈ **N**, *i* > 0, *delta*
  ∈ **Z**

That simply means our model has a value *val* to which we add some *delta*
(which is a positive or negative integer) at every simulation step. Our model
has the attribute *delta* (with value 1 by default) which can be changed by
control mechanisms to alter the behavior of the model. And it has the (output)
attribute *val* which is its current value.

.. figure:: /_static/example-model.*
   :width: 225
   :align: center
   :alt: Schematic diagram of our example model.

   Schematic diagram of our example model. You can change the *delta* and
   collect the *val* as output.

.. _model_python:

Here is a possible implementation of that simulation model in Python:

.. literalinclude:: code/example_model.py

.. _simulator_class:

Setup for the API implementation
================================

So lets start implementing mosaik's Sim-API for this model. We can use the
Python :doc:`high-level API </mosaik-api/high-level>` for this. This package
eases our workload, because it already implements everything necessary for
communicating with mosaik. It provides an abstract base class which we can
sub-class. So we only need to implement four methods and we are done.

If you already :doc:`installed </installation>` mosaik and the demo, you
already have this package installed in your mosaik virtualenv.

We start by creating a new :file:`simulator_mosaik.py` and import the module
containing the mosaik API as well as our model:

.. literalinclude:: code/simulator_mosaik.py
   :lines: 1-8

.. _meta_data:

Simulator meta data
===================

Next, we prepare the meta data dictionary that tells mosaik which
:ref:`time paradigm <time_paradigms>` it follows (*time-based*, *event-based*,
or *hybrid*), which models our simulator implements and which parameters and
attributes it has. Since this data is usually constant, we define this at
module level (which improves readability):

.. literalinclude:: code/simulator_mosaik.py
   :lines: 11-20

In this case we create a *time-based* simulator.
We added our "ExampleModel" model with the parameter *init_val* and the
attributes *delta* and *val*. At this point we don't care if they are inputs
or outputs. We just list everything we can read or write.  The *public* flag
should usually be ``True``. You can read more about it in the :ref:`Sim API
docs <api.init>`. From this information, mosaik deduces that our model could
be used in the following way:

.. code-block:: python

   # Model name and "params" are used for constructing instances:
   model = ExampleModel(init_val=42)
   # "attrs" are normal attributes:
   print(model.val)
   print(model.delta)

.. _mosaik_API:

The ``Simulator`` class
=======================

The package ``mosaik_api`` defines a base class ``Simulator`` for which we now
need to write a sub-class:

.. literalinclude:: code/simulator_mosaik.py
   :lines: 23-27

In our simulator's ``__init__()`` method (the constructor) we need to call
``Simulator.__init__()`` and pass the meta data dictionary to it.
``Simulator.__init__()`` will add some more information to the meta data and
set it as ``self.meta`` to our instance.

We also set a prefix for our entity IDs and prepare a dictionary which will
hold some information about the entities that we gonna create.

We can now start to implement the four API calls ``init``, ``create``, ``step``
and ``get_data``:

init()
======

This method will be called exactly once while the simulator is being started
via :meth:`World.start()`.
It is used for additional initialization tasks (e.g., it can handle parameters
that you pass to a simulator in your scenario definition). It must return the
meta data dictionary ``self.meta``:

.. literalinclude:: code/simulator_mosaik.py
   :lines: 29-35

The first argument is the ID that mosaik gave to that simulator instance. The
second argument is the :ref:`time resolution <time_resolution>` of the
scenario. In this example only the default value of *1.* (second per integer
time step) is supported. If you set another value in the scenario, the
simulator would throw an error and stop.

In addition to that, you can define further (optional) parameters which you
can later set in your scenario. In this case, we can optionally overwrite the
``eid_prefix`` that we defined in ``__init__()``.


create()
========

``create()`` is called in order to initialize a number of simulation model
instances *(entities)* within that simulator. It must return a list with some
information about each entity created:

.. literalinclude:: code/simulator_mosaik.py
   :lines: 37-47

The first two parameters tell mosaik how many instances of which model you
want to create. As in ``init()``, you can specify additional parameters for
your model. They must also appear in the *params* list in the simulator meta
data or mosaik will reject them. In this case, we allow setting the initial
value *init_val* for the model instances.

For each entity, we create a new entity ID [#]_ and a model instance. We also
create a mapping (``self.entities``) from the entity ID to our model. For each
entity we create we also add a dictionary containing its ID and type to the
``entities`` list which is returned to mosaik. In this example, it has *num*
entries for the model *model*, but it may get more complicated if you have,
e.g., hierarchical models.

.. [#] Although entity IDs can be plain integers, it is advisable to use
   something more meaningful to ease debugging and analysis.


step()
======

The ``step()`` method tells your simulator to perform a simulation step. It
receives its current simulation time, a dictionary with input values
from other simulators (if there are any), and the time until the simulator can
safely advance its internal time without creating a causality error. For
time-based simulators (as in our example) it can be safely ignored (it is
equal to the end of the simulation then). The method returns to mosaik the
time at which it wants to do its next step. For event-based and hybrid
simulators a next (self-)step is optional. If there is no next self-step, the
return value is None/null.

.. literalinclude:: code/simulator_mosaik.py
   :lines: 49-60

.. _inputs:

In this example, the *inputs* could be something like this:

.. code-block:: python

   {
       'Model_0': {
           'delta': {'src_id_0': 23},
       },
       'Model_1':
           'delta': {'src_id_1': 42},
       },
   }

The inner dictionaries containing the actual values may contain multiple
entries if multiple source entities provide input for another entity. The
simulator receiving these inputs is responsible for aggregating them (e.g., by
taking their sum, minimum or maximum. Since we are not interested in the
source's IDs, we convert that dict to a list with ``values.values()`` before we
calculate the sum of all input values.

After we converted the inputs to something that our simulator can work with,
we let it finally perform its next simulation step.

The return value ``time + 1`` tells mosaik that we wish to perform the next
step in one second (in simulation time), as the *time_resolution* is 1.
(second per integer step). Instead of using a fixed (hardcoded) step size you
can easily implement any other stepping behavior.


get_data()
==========

The ``get_data()`` call allows other simulators to get the values of the
``delta`` and ``val`` attributes of our models (the attributes we listed in
the simulator meta data):

.. literalinclude:: code/simulator_mosaik.py
   :lines: 62-72

.. _outputs:

The *outputs* parameter contains the query and may in our case look like this:

.. code-block:: python

   {
       'Model_0': ['delta', 'value'],
       'Model_1': ['value'],
   }

The expected return value would then be:

.. code-block:: python

   {
       'Model_0': {'delta': 1, 'value': 24},
       'Model_1': {'value': 3},
   }

In our implementation we loop over each entity ID for which data is requested.
We then loop over all requested attributes and check if they are valid. If so,
we dynamically get the requested value from our model instance via
``getattr(obj, 'attr')``. We store all values in the ``data`` dictionary and
return it when we are done.


Making it executable
====================

The last step is adding a ``main()`` method to make our simulator executable
(e.g., via ``python -m simulator_mosaik HOST:PORT``). The package
``mosaik_api`` contains the method ``start_simulation()`` which creates
a socket, connects to mosaik and listens for requests from it. You just call it
in your ``main()`` and pass an instance of your simulator class to it:

.. literalinclude:: code/simulator_mosaik.py
   :lines: 77-82

Simulators running on different nodes than the mosaik instance are supported
explicitly with the mosaik Python-API v2.4 upward via the **remote** flag. A simulator
with the ``start_simulation()`` method in its ``main()`` can then be called e.g. via

.. code-block:: bash

    python simulator_mosaik –r HOST:PORT

in the command line. The mosaik scenario, started
independently, can then connect to the simulator via the statement connect: ``HOST:PORT``
in its "*sim_config*"
( :raw-html:`&rarr;` `Configuration) <https://mosaik.readthedocs.io/en/latest/tutorials/demo1.html#configuration>`_.
Note that it may make sense to introduce a short waiting
time into your scenario to give you enough time to start both processes. Alternatively,
the remote connection of simulators supports also a timeout (via the **timeout** flag,
e.g. **–t 60** in the command line call will cause your simulator to wait for 60 seconds
for an initial message from mosaik).


Summary
=======

We have now implemented the mosaik Sim-API for our simulator. The following
listing combines all the bits explained above:

.. literalinclude:: code/simulator_mosaik.py

We can now start to write our first scenario, which we will do in the next
section.
