.. _examplesim:

========================================================
Integrating a simulation model into the mosaik ecosystem
========================================================

In this section we'll first implement a simple example simulator. We'll then
implement mosaik's SimAPI step-by-step


The simulator
=============

We want to implement a simulator for a very simple model with a discrete step
size of 1. Our model will have the following behavior:

- *val*:sub:`0` = *init_val*

- *val*:sub:`i` = *val*:sub:`i − 1` + *delta* for *i* ∈ **N**, *i* > 0, *delta*
  ∈ **Z**

That simply means our model has a value *val* to which we add some *delta*
(which is a positive or negative integer) at every simulation step. Our model
has the (optional) input *delta* which can be used by control mechanisms to
alter the behavior of the model. It has the output *val* which is its current
value.

.. figure:: /_static/example-model.*
   :width: 225
   :align: center
   :alt: Schematic diagram of our example model.

   Schematic diagram of our example model. You can change the *delta* input and
   collect the *val* output.

Here is a possible implementation of that simulation model in Python:

.. literalinclude:: code/simulator.py

If you run this script, you'll get the following output:

.. literalinclude:: code/simulator.out


Setup for the API implementation
================================

So lets start implementing mosaik's Sim API for this simulator. We can use the
Python :doc:`high-level API </mosaik-api/high-level>` for this. This package
eases our workload, because it already implements everything necessary for
communicating with mosaik. It provides an abstract base class which we can
sub-class. So we only need to implement four methods and we are done.

If you already :doc:`installed </installation>` mosaik and the demo, you
already have this package installed in your mosaik virtualenv.

We start by creating a new :file:`simulator_mosaik.py` and import the module
containing the mosaik API as well as our simulator:

.. literalinclude:: code/simulator_mosaik.py
   :lines: 1-8


Simulator meta data
===================

Next, we prepare the meta data dictionary that tells mosaik which models our
simulator implements and which parameters and attributes it has. Since this
data usually constant, we defines this at module level (which improves
readability):

.. literalinclude:: code/simulator_mosaik.py
   :lines: 11-19

We added our "Model" model with the parameter *init_val* and the attributes
*delta* and *val*. At this point we don't care if they are read-only or not. We
just list everything we can read or write.  The *public* flag should usually be
``True``. You can read more about it in the :ref:`Sim API docs <api.init>`.
From this information, mosaik deduces that our model could be used in the
following way:

.. code-block:: python

   # Model name and "params" are used for constructing instances:
   model = ExampleModel(init_val=42)
   # "attrs" are normal attributes:
   print(model.val)
   print(model.delta)


The ``Simulator`` class
=======================

The package ``mosaik_api`` defines a base class ``Simulator`` for which we now
need to write a sub-class:

.. literalinclude:: code/simulator_mosaik.py
   :lines: 22-27

In our simulator's ``__init__()`` method (the constructor) we need to call
``Simulator.__init__()`` and pass the meta data dictionary to it.
``Simulator.__init__()`` will add some more information to the meta data and
set it as ``self.meta`` to our instance.

We also initialize our actual simulator class, set a prefix for our entity IDs
and prepare a dictionary which will hold some information about the entities
that we gonna create.

We can now start to implement the four API calls ``init``, ``create``, ``step``
and ``get_data``:

init()
======

This method will be called exactly once after the simulator has been started.
It is used for additional initialization tasks (e.g., it can handle parameters
that you pass to a simulator in your scenario definition). It must return the
meta data dictionary ``self.meta``:

.. literalinclude:: code/simulator_mosaik.py
   :lines: 29-32

The first argument is the ID that mosaik gave to that simulator instance. In
addition to that, you can define further (optional) parameters which you can
later set in your scenario. In this case, we can optionally overwrite the
``eid_prefix`` that we defined in ``__init__()``.


create()
========

``create()`` is called in order to initialize a number of simulation model
instances *(entities)* within that simulator. It must return a list with some
information about each entity created:

.. literalinclude:: code/simulator_mosaik.py
   :lines: 34-44

The first two parameters tell you how many instances of which model you should
create. As in ``init()``, you can specify additional parameters for your model.
They must also appear in the *params* list in the simulator meta data or mosaik
will reject them. In this case, we allow setting the initial value *init_val*
for the model instances.

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
returns to mosaik the time at which it it wants to to its next step. It
receives its current simulation time as well as a dictionary with input values
from other simulators (if there are any):

.. literalinclude:: code/simulator_mosaik.py
   :lines: 46-58

In this example, the *inputs* could be something like this:

.. code-block:: python

   {
       'Model_0': {
           'delta': {'src_eid_0': 23},
       },
       'Model_1':
           'delta': {'src_eid_1': 42},
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

The return value ``time + 60`` tells mosaik that we wish to perform the next
step in one minute (in simulation time).


get_data()
==========

The ``get_data()`` call allows other simulators to get the values of the
``delta`` and ``val`` attributes of our models (the attributes we listed in
the simulator meta data):

.. literalinclude:: code/simulator_mosaik.py
   :lines: 60-73

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
   :lines: 76-81


Summary
=======

We have now implemented the mosaik Sim API for our simulator. The following
listing combines all the bits explained above:

.. literalinclude:: code/simulator_mosaik.py

We can now start to write our first scenario, which is exactly what the next
section is about.
