==============
Modular Design
==============

Mosaik as a co-simulation tool organizes the data exchange between simulators
and coordinates the execution of the connected simulaters. This part is called
|mosaik| ``mosaik-core``.

    .. figure:: /_static/mosaik-ecosystem.*
       :figwidth: 550
       :width: 550
       :align: center
       :alt: mosaik is a co-simulation library. The components and tools
             form the mosaik ecosystem.

       Mosaik is a co-simulation library. The components and tools
       form the mosaik ecosystem.


Mosaik-core without any connected simulators doesn't do much. This is why we
provide some simple and free simulators so that it is possible to start with
a working Smart-Grid simulation. These simulators belong to a part of mosaik's ecosystem called |mosaik| ``mosaik-components``.

Mosaik is developed following the "lean and mean" principle. That means that we
try to keep the software as simple as possible in order to keep it efficient
and easy to maintain.  In order to make it easier to set up and run experiments with
mosaik we provide some tools that help building scenarios, connecting
simulators or to visualize and analyze the simulation results. These tools are
located in the |mosaik| ``mosaik-tools``-library.

---------------------------------

**Elements of the mosaik ecosystem:**

.. |mosaik| ``mosaik-components``

.. mosaik-demo (coming soon...)

|mosaik| ``mosaik-tools``

.. toctree::
   :maxdepth: 1

   Odysseus-adapter <odysseus>


.. |mosaik| image:: /_static/favicon.ico
