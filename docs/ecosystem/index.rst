================
mosaik ecosystem
================

Mosaik as a co-simulation tool organizes the data exchange between simulators
and coordinates the execution of the connected simulaters. This part is called
|mosaik| :ref:`mosaik_core` and contains mosaik itself and APIs for multiple
programming languages.

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
a working Smart-Grid simulation. These simulators belong to a part of mosaik's ecosystem called
|mosaik| :ref:`mosaik_components`.

To see how these components can be coupled to simulations, also some example scenarios are
provided in |mosaik| :ref:`mosaik_examples`.

Mosaik is developed following the "lean and mean" principle. That means that we
try to keep the software as simple as possible in order to keep it efficient
and easy to maintain.  In order to make it easier to set up and run experiments with
mosaik we provide some tools that help building scenarios, connecting
simulators or to visualize and analyze the simulation results. These tools are
located in the |mosaik| :ref:`mosaik_tools`-library.

There are also some implementations done by external users of mosaik. We give an overview
of the |mosaik| :ref:`external_components` we know here.

.. _mosaik_core:

|mosaik| mosaik-core
====================

The `root folder <https://gitlab.com/mosaik>`_ contains mosaik itself and the high-level API implementations are
provided in the `API folder <https://gitlab.com/mosaik/api>`_.

- `mosaik <https://gitlab.com/mosaik/mosaik>`_
- `API for Python <https://gitlab.com/mosaik/mosaik-api-python>`_
- `API for Java <https://gitlab.com/mosaik/mosaik-api-java>`_
- `generics for Java API <https://gitlab.com/mosaik/api/mosaik-api-java-generics>`_
-  :doc:`Java tutorial </tutorials/tutorial_api-java>`
- `API for Matlab <https://gitlab.com/mosaik/matlab-mosaik-toolbox>`_
- `API for C# <https://gitlab.com/mosaik/mosaik-api-c-sharp>`_

.. _mosaik_components:

|mosaik| mosaik-components
==========================

- `energy <https://gitlab.com/mosaik/components/energy>`_ related components:

    - `mosaik-pandapower <https://gitlab.com/mosaik/components/energy/mosaik-pandapower>`_
      is an adapter for the `pandapower <http://www.pandapower.org/>`_ power system
      modeling, analysis and optimization tool.

    - `mosaik-pypower <https://gitlab.com/mosaik/components/energy/mosaik-pypower>`_ is an
      adapter for the `PYPOWER <https://github.com/rwl/PYPOWER>`_ load flow
      analysis library.

    - `mosaik-heatpump <https://gitlab.com/mosaik/components/energy/mosaik-heatpump>`_
      contains different models for simulation of heatpumps.

- `data <https://gitlab.com/mosaik/components/data>`_ related components:

    - `mosaik-web <https://gitlab.com/mosaik/components/data/mosaik-web>`_ is a web
      visualization for mosaik simulations.

    - `mosaik-csv <https://gitlab.com/mosaik/components/data/mosaik-csv>`_ and
      `mosaik-householdsim <https://gitlab.com/mosaik/components/energy/mosaik-householdsim>`_
      are simple demo simulators that you can use to integrate CSV data sets and
      load-profile based households into simulation.

    - `mosaik-hdf5 <https://gitlab.com/mosaik/components/data/mosaik-hdf5>`_ allows
      to write simulation results to a HDF5 file for further analysis.

    - `InfluxDB adapter <https://gitlab.com/mosaik/components/data/mosaik-influxdb>`_ to store simulation
      results into InfluxDB 1 time series database.

    - `InfluxDB 2 adapter <https://gitlab.com/mosaik/components/data/mosaik-influxdb2>`_ to store simulation
      results into InfluxDB 2 time series database.

    - `ZeroMQ adapter <https://gitlab.com/mosaik/components/data/mosaik-zmq>`_ to connect components
      with the messaging library ZeroMQ.

    - :doc:`Odysseus-adapter </tutorials/odysseus>` to write results to the data stream management system
      `Odysseus <https://odysseus.informatik.uni-oldenburg.de/>`_ to mosaik.

- `FMI adapter <https://gitlab.com/mosaik/components/mosaik-fmi>`_ allows to couple Functional Mockup Units (FMU),
  which are based on the `FMI standard <https://fmi-standard.org>`_.
- `communication simulator <https://gitlab.com/mosaik/components/communication/mosaik-communication>`_ is a
  basic communication suite using delays.

.. _mosaik_examples:

|mosaik| mosaik-examples
========================

- The `mosaik-demo <https://gitlab.com/mosaik/examples/mosaik-demo>`_
  contains a simple demo scenario for mosaik.

- The `DES demo <https://gitlab.com/mosaik/examples/des_demos>`_ is a simple example
  scenario showing the new mosaik 3.0 DES features

- `COmmunication SIMulation for Agents (cosima) <https://gitlab.com/mosaik/examples/cosima>`_ is an example scenario
  with integrated communication simulation based on OMNeT++.

.. _mosaik_tools:

|mosaik| mosaik-tools
=====================

- `icons for the energy domain <https://gitlab.com/mosaik/tools/energy-icons>`_
- `maverig mosaik GUI <https://gitlab.com/mosaik/tools/maverig>`_ is a visualization component, which is
  not maintained anymore.

.. _external_components:

|mosaik| external components
============================

These components are developed by external users of mosaik and we can not guarantee or support
the flawless integration of these tools with mosaik.
If you also have implemented additional tools for mosaik, simulation models or adapters,
feel free to contact us at `mosaik [ A T ] offis.de <mosaik@offis.de>`_ to be listed here.

- `pysimmods <https://gitlab.com/midas-mosaik/pysimmods>`_ contains some simulation models,
  which can be used in mosaik scenarios.

- `MIDAS <https://gitlab.com/midas-mosaik/midas>`_ contains a semi-automatic scenario configuration
  tool.

- `mosaik-docker <https://github.com/ERIGrid2/mosaik-docker>`_ is a package for the deployment
  of mosaik with Docker.

- `ZDIN-ZLE <https://gitlab.com/zdin-zle>`_ contains the research and development of digitalized
  energy systems in ZLE using mosaik (collection of simulation models and scenarios).


.. |mosaik| image:: /_static/favicon.png
