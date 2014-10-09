========
Tutorial
========

In this tutorial you'll learn how you can integrate simulators and control
strategy into the mosaik ecosystem as well as how you create simulation
scenarios and execute them.

In the first part, we'll implement the Sim API for a simple example simulator.
We'll also create a simulation scenario in which that simulator will send its
data to `mosaik-hdf5 <https://pypi.python.org/pypi/mosaik-hdf5>`_ which will
store it in an HDF5 database.

In the second part, we'll also integrate a simple control mechanism into
mosaik. We'll then create a scenario in which that control mechanism controls
the example simulator from part one.


1.1 Integrating a simulation model into the mosaik ecosystem
============================================================

In this section we'll first implement a simple example simulator. We'll then
implement mosaik's SimAPI step-by-step


The simulator
-------------

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

Setup for the API implementation
--------------------------------

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
-------------------

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
   model = Model(init_val=42)
   # "attrs" are normal attributes:
   print(model.val)
   print(model.delta)


The ``Simulator`` class
-----------------------

...


1.2 Creating and runjning simple simulation scenarios
=====================================================


2.1 Integrating a control mechanism
===================================


2.2 Adding a control mechanism to a scenario
============================================


