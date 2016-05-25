=========
Tutorials
=========

In the **basic tutorial** you'll learn how you can integrate simulators and control
strategy into the mosaik ecosystem as well as how you create simulation
scenarios and execute them.

In the first part, we'll implement the Sim API for a simple example simulator.
We'll also create a simulation scenario in which that simulator will send its
data to `mosaik-hdf5 <https://pypi.python.org/pypi/mosaik-hdf5>`_ which will
store it in an HDF5 database.

In the second part, we'll also integrate a simple control mechanism into
mosaik. We'll then create a scenario in which that control mechanism controls
the example simulator from part one.

The **Odysseus tutorial** you'll learn how to connect the data-stream-management-tool
Odysseus to mosaik. The second part shows some examples on how to use Odysseus. 
This tutorial may also be of some use when you want to connect any other component
via ZeroMQ.

The **Java API tutorial** shows you how to use the Java API. This API is intended to 
connect simulators written in Java to mosaik. You can use the Java-API also as a 
RCP-Server if you want to run your Java-simulator on a separate machine.

Basic tutorial

.. toctree::
   :maxdepth: 1

   examplesim
   demo1
   examplectrl
   demo2

Odysseus tutorial

.. toctree::
   :maxdepth: 1

   odysseus
   odysseus2

Java API tutorial

.. toctree::
   :maxdepth: 1

   tutorial_api-java
