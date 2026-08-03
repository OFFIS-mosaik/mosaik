================
mosaik ecosystem
================

mosaik as a co-simulation tool organizes the data exchange between simulators and coordinates the execution of the connected simulators.
This part is called the *mosaik core*.
To become useful, other components need to be connected to it; these other components form the *mosaik ecosystem*.

    .. figure:: /_static/mosaik-ecosystem.*
       :figwidth: 550
       :width: 550
       :align: center
       :alt: mosaik is a co-simulation library. The components and tools
             form the mosaik ecosystem.

       mosaik is a co-simulation library. The components and tools
       form the mosaik ecosystem.

The ecosystem consists of pre-made bindings to programming languages that make connecting your own simulators easier, see :doc:`/mosaik-api/high-level-other-languages`, and of pre-made bindings to simulation tools, which are listed below.

While not strictly part of the ecosystem, we also list some :ref:`example scenarios below <mosaik-examples>` to show how these tools can be coupled, and :ref:`some tools <mosaik-tools>` which help with the building of scenarios and the visualization and analysis of results.


.. _mosaik-components:

mosaik components
-----------------

Here is a list of simulators that are already connected to mosaik.
Most of them are available on PyPI and may therefore be installed using ``pip`` or your favorite Python package manager.
For simulators that are not available there, we link to their repositories, instead.

The couplings (though usually not the underlying simulation tools) marked with |mosaik| are developed by us; the others are developed elsewhere.
If you have a mosaik simulator that is publically available and might be of use to others, feel free to contact us (`mosaik@offis.de <mosaik@offis.de>`__) so we can add it to this list. Please provide a short summary (3 to 5 lines) of your simulator's capabilities (similar to the ones below) when you do.


Basic components
^^^^^^^^^^^^^^^^

|mosaik| :doc:`InputSimulator <basic_simulators>`.
Provide constant values or values calculated by a simple Python function to the rest of the simulation.
This is mostly intended for test purposes.
In real simulations, this will often be replaced by one of the `input simulators`_.

|mosaik| :doc:`OutputSimulator <basic_simulators>`.
Collect values in Python dicts and access them in your scenario script after the simulation is over.
This is mostly intended for test purposes; in real simulations you would usually employ one of the `output simulators`_, instead.


.. _energy-sims:

Energy-related components
^^^^^^^^^^^^^^^^^^^^^^^^^

|mosaik| `mosaik-pandapower-2 <https://pypi.org/project/mosaik-pandapower-2/>`__.
Load a `pandapower <http://www.pandapower.org/>`__ electrical grid and simulate its load flows after connecting mosaik components representing loads and generators to its buses.
The state of the buses and lines can be read.
If `SimBench` is installed, its grids with included time series for their loads and generators may also be used.

|mosaik| `mosaik-pandapipes <https://pypi.org/project/mosaik-pandapipes>`__.
Load a `pandapipes <https://www.pandapipes.org/>`__ fluid network, connect sources and sinks represented by other simulators to it, calculate its pipeflow and then pass on the state of the pipes and junctions to other parts of your simulation.

|mosaik| `mosaik-heatpump <https://pypi.org/project/mosaik-heatpump>`__.
Model heat systems consisting of heat pumps, hot water tanks and controllers. This adapter has `detailed documentation here <https://mosaik-heatpump-docs.readthedocs.io/>`__.

|mosaik| `mosaik-pv <https://pypi.org/project/mosaik-pv>`__.
Simulate PV active power from direct normal irradiance (DNI) and time alone, in hourly resolution.
(Based on PyPVSim.)

|mosaik| `mosaik-pvlib <https://pypi.org/project/mosaik-pvlib>`__.
Simulate PV systems using PVLib, which requires detailed weather data: global irradiance, wind speed, air temparature, and air pressure, which you will need to provide.
This adapter computes both active and reactive power.
Three predefined PV configurations are included: house, building, and simple.

|mosaik| `mosaik-pvgis <https://pypi.org/project/mosaik-pvgis>`__.
Simulate PV systems using historical data from PVGIS, which means that no weather data is required.
Instead, you specify the system's configuration, geographic location, and a reference year.
The default resolution is hourly, but intermediate values can be interpolated.

`mosaik-demod <https://github.com/epfl-herus/mosaik-demod>`__.
Model domestic energy demand.

.. _input simulators:

Input simulators
^^^^^^^^^^^^^^^^

|mosaik| `mosaik-csv <https://pypi.org/project/mosaik-csv>`__.
Read (and write) CSV files following a slightly adapted format.
This is generally useful if you want to inject existing time-series into your simulation, for example historic price or weather data.


.. _output simulators:

Output and visualization
^^^^^^^^^^^^^^^^^^^^^^^^

|mosaik| `mosaik-web <https://pypi.org/project/mosaik-web>`__.
Visualize (parts of) your simulation as an automatically laid-out grid and show live data for one attribute per node.
This is mostly useful if the main component in your simulation is a simulator for electrical grids.

|mosaik| `mosaik-csv <https://pypi.org/project/mosaik-csv>`__.
Write data from your simulation to a CSV file.
Timestamps based on the current simulated time will be added automatically.

|mosaik| `mosaik-hdf5 <https://pypi.org/project/mosaik-hdf5>`__.
Write resulst from your simulation to an HDF5 file.

|mosaik| `InfluxDB 2 <https://pypi.org/project/mosaik-influxdb2>`__.
Write data from your simulation into an `InfluxDB 2 database <https://docs.influxdata.com/influxdb/v2/>`__, with timestamps based on the simulated time.
You can add a measurement name to identify the simulation run, and the data's source entity information will be stored in tags.

|mosaik| `mosaik-timescaledb <https://gitlab.com/mosaik/components/data/mosaik-timescaledb>`_
Store your simulation outputs in a PostgreSQL database, potentially with TimescaleDB integrated.
The adapter can use your existing database structure or create it for you based on the connected attributes.
You can also specify run IDs to store data for multiple runs in the same database.


Messaging protocols
^^^^^^^^^^^^^^^^^^^

|mosaik| `ZeroMQ <https://gitlab.com/mosaik/components/data/mosaik-zmq>`__.
Read and write data from a ZeroMQ connection.

|mosaik| `mosaik-104 <https://gitlab.com/mosaik/components/communication/mosaik-104>`__. Connect mosaik to something via the IEC 60870-5-104 protocol.
This adapter is relatively limited in the amount of data that can be transmitted.


Communication simulation
^^^^^^^^^^^^^^^^^^^^^^^^

|mosaik| `mosaik-omnet <https://gitlab.com/mosaik/components/communication/mosaik-omnet>`__.
Connect the discrete event simulator `OMNeT++` (or its commercial cousin OMNEST) to mosaik.
In OMNeT++, you use a special scheduler and write modules that can be called with data from mosaik and send data back to mosaik.
For the common case that OMNeT++ is used to simulate a communication infrastructure with the INET framework, special *apps* are provided as a further simplification.

|mosaik| `communication simulator <https://gitlab.com/mosaik/components/communication/mosaik-communication>`__.
Simulate communication as delays.


Other general simulation tools
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

|mosaik| `mosaik-mango <https://pypi.org/project/mosaik-mango>`__.
Connect a multi-agent simulation written in the framework `mango <https://mango.offis.de/>`__ to mosaik.
Special mosaik agents in the agent simulation will appear as entities in the mosaik simulation.
Input from mosaik will result in these agents being called, and they can also send data back to mosaik.
For this, time between both frameworks is synchronized.

|mosaik| `moped <https://gitlab.offis.de/official/fbe-p_recode_ext/mosaik-opsim>`__.
Connect the co-simulation framework `OpSim <https://www.iee.fraunhofer.de/de/anwendungsfelder/energienetze/opsim.html>`__ to mosaik.
This allows either framework access to simulators connected to the other, at the cost of a more involved set-up and slightly increased simulation time.

|mosaik| `FMI adapter <https://gitlab.com/mosaik/components/mosaik-fmi>`__.
Use Functional Mockup Units (FMU) (based on the `FMI standard <https://fmi-standard.org>`__) as simulators in mosaik.


Simulator packages
^^^^^^^^^^^^^^^^^^

These are packages of multiple simulators, that therefore do not cleanly integrate into one of the categories above.

`pysimmods <https://gitlab.com/midas-mosaik/pysimmods>`__.
Simulation models for different parts of the energy system.

`ZDIN-ZLE components <https://gitlab.com/zdin-zle/models>`__.
Models for digitalized energy systems from ZLE.

`QEMS - Quarter Energy Management System <https://gitlab.com/qems/scenarios>`__.
Simulate an energy management system for neighborhoods for analyzing and optimizing energy flows.

Outdated simulators
^^^^^^^^^^^^^^^^^^^

The following simulators still exist, but are not actively maintained.
We recommend that you do not use them for new mosaik simulations.

|mosaik| `InfluxDB adapter <https://gitlab.com/mosaik/components/data/mosaik-influxdb>`__.
Store data from your simulation in an InfluxDB 1 time series database.

|mosaik| `mosaik-sql adapter <https://gitlab.com/mosaik/components/data/mosaik-sql>`__.
Store simulation results into SQL database.
If you are using a PostgreSQL database, we recommend that you use the mosaik-timescaledb adapter, instead.


|mosaik| :doc:`Odysseus-adapter </tutorials/odysseus>`.
Write results to the data stream management system `Odysseus <https://odysseus.informatik.uni-oldenburg.de/>`__.

|mosaik| `mosaik-pypower <https://gitlab.com/mosaik/components/energy/mosaik-pypower>`__.
Simulate load flows using the `PYPOWER <https://github.com/rwl/PYPOWER>`__ library.
This adapter is not actively maintained anymore.
We recommend that you use *mosaik-pandapower-2*, :ref:`mentioned above <energy-sims>`, instead.

|mosaik| `mosaik-householdsim <https://gitlab.com/mosaik/components/energy/mosaik-householdsim>`__.
Simulate households based on residual load profiles.
This simulator is tightly integrated with the *mosaik-PYPOWER* adapter.


.. _mosaik-examples:

Example simulations
-------------------

The following repositories contain scenarios using mosaik, which might be helpful to learn from.
Scenarios marked with |mosaik| are developed by us; the others are developed elsewhere.

If you have a publically accessible scenario, feel free to reach out to us to have it included in this list.
Ideally, you provide a short description with it.

|mosaik| The `mosaik-demo <https://gitlab.com/mosaik/examples/mosaik-demo>`__ contains a simple demo scenario for mosaik.

|mosaik| The `DES demo <https://gitlab.com/mosaik/examples/des_demos>`__ is a simple example scenario showing the new mosaik 3.0 DES features

|mosaik| `COmmunication SIMulation for Agents (cosima) <https://gitlab.com/mosaik/examples/cosima>`__ is an example scenario with integrated communication simulation based on OMNeT++.

|mosaik| The `aiomas demo <https://gitlab.com/mosaik/examples/mosaik-aiomas-demo>`__ is an example project, demonstrating how to couple a multi-agent system written in aiomas to mosaik.

|mosaik| The `mango demo <https://gitlab.com/mosaik/examples/mosaik-mango-demo>`__ is an example project, demonstrating how to couple a multi-agent system written in mango to mosaik.

|mosaik| The `binder tutorials <https://gitlab.com/mosaik/examples/mosaik-tutorials-on-binder>`_ contains python notebooks with example scenraios that can be executed on mybinder.

`Benchmark Model Multi-Energy Networks <https://github.com/ERIGrid2/benchmark-model-multi-energy-networks/tree/mooc-demo>`__ contains the implementation of a multi-energy networks (heat and electricity grid) benchmark model developed in the `ERIGrid 2.0 <https://erigrid2.eu/>`_ project.

`Benchmark Model Multi-Energy Networks STL <https://github.com/ERIGrid2/JRA-2.1.3-STL>`__ is based on the multi-energy networks benchmark and contains a same time loop for improved initialization of the simulators.

`ZDIN-ZLE scenarios <https://gitlab.com/zdin-zle/scenarios>`__ contains the research and development of digitalized energy systems in ZLE using mosaik (collection of simulation scenarios).

`QEMS - Quarter Energy Management System Scenarios <https://gitlab.com/qems/scenarios>`__ contains scenarios of an energy management system for neighborhoods for analyzing and optimizing energy flows.

`nestli <https://github.com/hues-platform/nestli>`__ (Neighborhood Energy System Testing towards Large-scale Integration) is a co-simulation environment for benchmarking the performance of BACS (building automation and control systems).
Is uses EnergyPlus and FMUs with mosaik.


.. _mosaik-tools:

mosaik tooling
--------------

- `icons for the energy domain <https://gitlab.com/mosaik/tools/energy-icons>`_
- `maverig mosaik GUI <https://gitlab.com/mosaik/tools/maverig>`__ is a visualization component, which is not maintained anymore.
- `MIDAS <https://gitlab.com/midas-mosaik/midas>`__ is a semi-automatic scenario configuration tool.
- `mosaik-docker <https://github.com/ERIGrid2/mosaik-docker>`__ is a package for the deployment of mosaik with Docker.
- `toolbox_doe_sa <https://github.com/ERIGrid2/toolbox_doe_sa>`__ is a toolbox with Design of Experiment (DoE) and Sensitivity Analysis (SA) methods developed in the `ERIGrid 2.0 <https://erigrid2.eu/>`_ project.
- `palestrai-mosaik <https://gitlab.com/arl2/palaestrai-mosaik>`__ is an adapter to integrate `palaestrAI <https://palaestr.ai>`__ (an universal framework for multi-agent artificial intelligence) into mosaik.
