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

Contents of the tutorial:

.. toctree::
   :maxdepth: 1

   examplesim
   demo1
   examplectrl
   demo2
