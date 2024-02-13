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
of the |mosaik| :ref:`external_components` and |mosaik| :ref:`external_scenarios` we know here.

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
- `API for Matlab via Java <https://gitlab.com/mosaik/api/mosaik-api-matlab-over-java>`_
- `API for C# <https://gitlab.com/mosaik/mosaik-api-c-sharp>`_

.. _mosaik_components:

|mosaik| mosaik-components
==========================
This lists the mosaik components that are available on pypi. There are always component in work that are not released yet but are in working condition so if you don't find what you are searching for here take a look in the repository.

- `energy <https://gitlab.com/mosaik/components/energy>`_ related components:

    - `mosaik-pandapower <https://gitlab.com/mosaik/components/energy/mosaik-pandapower>`_
      is an adapter for the `pandapower <http://www.pandapower.org/>`_ power system
      modeling, analysis and optimization tool. Not maintained anymore, please install the `mosaik-pandapower2 <https://gitlab.com/mosaik/components/energy/mosaik-pandapower-2>`_ adapter.

    - `mosaik-pandapipes <https://gitlab.com/mosaik/components/energy/mosaik-pandapipes>`_
      is an adapter for the `pandapipes <https://www.pandapipes.org/>`_ fluid system modeling, analysis and optimization tool.

    - `mosaik-pypower <https://gitlab.com/mosaik/components/energy/mosaik-pypower>`_ is an
      adapter for the `PYPOWER <https://github.com/rwl/PYPOWER>`_ load flow
      analysis library. Not maintained anymore, please install the `mosaik-pandapower2 <https://gitlab.com/mosaik/components/energy/mosaik-pandapower-2>`_ adapter.

    - `mosaik-heatpump <https://gitlab.com/mosaik/components/energy/mosaik-heatpump>`_
      contains different models for simulation of heatpumps.

    - `mosaik-pv <https://gitlab.com/mosaik/components/energy/mosaik-pv>`_
      is a simple PV Simulator based on PyPVSim.

    - `mosaik-pvlib <https://gitlab.com/mosaik/components/energy/mosaik-pvlib>`_
      is a simple PV Simulator based on pvlib.

    - `mosaik-pvgis <https://gitlab.com/mosaik/components/energy/mosaik-pvgis>`_
      is a simple PV Simulator based on PVGIS.

    - `mosaik-householdsim <https://gitlab.com/mosaik/components/energy/mosaik-householdsim>`_
      is a househol simulator that simulate households by serving residual load profiles.


- `data <https://gitlab.com/mosaik/components/data>`_ related components:

    - `mosaik-web <https://gitlab.com/mosaik/components/data/mosaik-web>`_ is a web
      visualization for mosaik simulations.

    - `mosaik-csv <https://gitlab.com/mosaik/components/data/mosaik-csv>`_ 
      is a simple demo simulators that you can use to integrate CSV data sets into simulation.
      It can also write data into CSV data sets.

    - `mosaik-hdf5 <https://gitlab.com/mosaik/components/data/mosaik-hdf5>`_ allows
      to write simulation results to a HDF5 file for further analysis.

    - `InfluxDB adapter <https://gitlab.com/mosaik/components/data/mosaik-influxdb>`_ to store simulation
      results into InfluxDB 1 time series database.

    - `InfluxDB 2 adapter <https://gitlab.com/mosaik/components/data/mosaik-influxdb2>`_ to store simulation
      results into InfluxDB 2 time series database.

    - `mosaik-sql adapter <https://gitlab.com/mosaik/components/data/mosaik-sql>`_ to store simulation
      results into SQL database.
    
    - `mosaik-timescaledb adapter <https://gitlab.com/mosaik/components/data/mosaik-timescaledb>`_ to store simulation
      results into a postgres or timescale database.

    - `ZeroMQ adapter <https://gitlab.com/mosaik/components/data/mosaik-zmq>`_ to connect components
      with the messaging library ZeroMQ.

    - :doc:`Odysseus-adapter </tutorials/odysseus>` to write results to the data stream management system
      `Odysseus <https://odysseus.informatik.uni-oldenburg.de/>`_ to mosaik.
      
- `communication <https://gitlab.com/mosaik/components/energy>`_ related components:
    
    - `communication simulator <https://gitlab.com/mosaik/components/communication/mosaik-communication>`_ is a
      basic communication suite using delays.

    - `mosaik-104 <https://gitlab.com/mosaik/components/communication/mosaik-104>`_ contains an adapter to receive IEC 60870-5-104 protocol
      messages and hands it over to mosaik.

- `FMI adapter <https://gitlab.com/mosaik/components/mosaik-fmi>`_ allows to couple Functional Mockup Units (FMU),
  which are based on the `FMI standard <https://fmi-standard.org>`_.
    
.. _mosaik_examples:

|mosaik| mosaik-examples
========================

- The `mosaik-demo <https://gitlab.com/mosaik/examples/mosaik-demo>`_
  contains a simple demo scenario for mosaik.

- The `DES demo <https://gitlab.com/mosaik/examples/des_demos>`_ is a simple example
  scenario showing the new mosaik 3.0 DES features

- `COmmunication SIMulation for Agents (cosima) <https://gitlab.com/mosaik/examples/cosima>`_ is an example scenario
  with integrated communication simulation based on OMNeT++.

- The `aiomas demo <https://gitlab.com/mosaik/examples/mosaik-aiomas-demo>`_ is an example project, demonstrating how to couple a 
  multi-agent system written in aiomas to mosaik.

- The `mango demo <https://gitlab.com/mosaik/examples/mosaik-mango-demo>`_ is an example project, demonstrating how to couple a 
  multi-agent system written in mango to mosaik.

- The `binder tutorials <https://gitlab.com/mosaik/examples/mosaik-tutorials-on-binder>`_ contains python notebooks with example scenraios that can be executed on mybinder.

.. _mosaik_tools:

|mosaik| mosaik-tools
=====================

- `icons for the energy domain <https://gitlab.com/mosaik/tools/energy-icons>`_
- `maverig mosaik GUI <https://gitlab.com/mosaik/tools/maverig>`_ is a visualization component, which is
  not maintained anymore.


|mosaik| mosaik simulators
==========================

.. include:: basic_simulators.rst


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

- `ZDIN-ZLE components <https://gitlab.com/zdin-zle/models>`_ contains the research and development of digitalized
  energy systems in ZLE using mosaik (collection of simulation models).

- `nestli <https://github.com/hues-platform/nestli>`_ (Neighborhood Energy System Testing towards Large-scale
  Integration) is a co-simulation environment for benchmarking the performance of BACS (building automation and
  control systems). Is uses EnergyPlus and FMUs with mosaik.

- `toolbox_doe_sa <https://github.com/ERIGrid2/toolbox_doe_sa>`_ is a toolbox with Design of Experiment (DoE) and
  Sensitivity Analysis (SA) methods developed in the `ERIGrid 2.0 <https://erigrid2.eu/>`_ project.

- `mosaik-demod <https://github.com/epfl-herus/mosaik-demod>`_ is a domestic energy demand modeling simulator.

- `palestrai-mosaik <https://gitlab.com/arl2/palaestrai-mosaik>`_ is an adapter to integrate
  `palaestrAI <https://palaestr.ai>`_ (an universal framework for multi-agent artificial intelligence)
  into mosaik.

.. _external_scenarios:

|mosaik| external scenarios
============================

These scenarios are developed by external users of mosaik and we can not guarantee or support
the flawless practicability.

- `Benchmark Model Multi-Energy Networks <https://github.com/ERIGrid2/benchmark-model-multi-energy-networks/tree/mooc-demo>`_
  contains the implementation of a multi-energy networks (heat and electricity grid) benchmark model
  developed in the `ERIGrid 2.0 <https://erigrid2.eu/>`_ project.

- `Benchmark Model Multi-Energy Networks STL <https://github.com/ERIGrid2/JRA-2.1.3-STL>`_ is based on the
  multi-energy networks benchmark and contains a same time loop for improved initialization of the simulators.

- `ZDIN-ZLE scenarios <https://gitlab.com/zdin-zle/scenarios>`_ contains the research and development of digitalized
  energy systems in ZLE using mosaik (collection of simulation scenarios).
