============
Requirements
============

This documents lists all requirements for mosaik's development. The main goals
are:

#. Couple existing :term:`simulators <simulator>`, schedule their (step-wise)
   execution and manage the data exchange between them.

   These simulators may range from open-source software to closed-source and
   commercial software as well as from simulators that can directly integrate
   the mosaik API to simulators that offer their own API and that cannot be
   started or directly controlled by mosaik.

#. Allow easy creation and execution of large-scale simulation :term:`scenarios
   <scenario>`.

   *Large-scale* means scenarios comprising thousands or ten thousands of
   simulated :term:`entities <entity>`. As few lines of code as possible should
   be required to describe a scenario and connect all entities involved.

   Once a scenario is defined, it should be easy to run the simulation.

#. Maintainability is most important.

   Developers will not be able to contribute to mosaik forever. New developers
   must be able to quickly understand how mosaik works in order to fix things
   and add features.

   Thus, the source code of mosaik must be as readable as possible. Everything
   should be documented (API docs *and* guides describing the ideas and
   concepts behind the different parts of mosaik). There should also be as
   little different technologies (and libraries to a certain point) involved as
   possible.

#. Runtime performance is important, too, but not as much as maintainability.

#. Stability and robustness: Large simulations (comprising thousands of
   entities over a period of several months or a year of simulation time) may
   take a while. Mosaik should not crash in the middle of a simulation, so
   everything needs to be tested as good as possible.

The following sections describe these requirements in more detail.


Types of simulators and models
------------------------------

#. Heterogeneous implementations: It must be possible to integrate simulators
   with different implementations (i.e., programming languages, frameworks,
   tools).

#. Different temporal resolutions: Mosaik must be able to compose simulations
   from models with differing temporal resolutions.

#. Multiple paradigms: Mosaik must be able to compose simulation models that
   use different paradigms with respect to the handling of time (e.g., discrete
   event or continuous).

#. Simulators written in Python (like mosaik) should be able to run in the same
   process as mosaik, so that no networking is required in order to communicate
   with them.

#. Mosaik must be able to start and stop (open-source) simulators that can
   directly implement the mosaik API. It should always use the fasted possible
   method to communicate with them; e.g., inter-process communication if the
   simulator runs on the same machine or sockets if it runs on another machine.

#. COTS integration: It must be possible to write adapters that translate
   between the mosaik API and the API provided by commercial or closed-source
   simulators.

   Mosaik also needs to handle simulators that it cannot start itself but can
   only connect to a running instance of them.

#. Real-time simulators: Mosaik must be able to work with real-time
   (wall-clock) simulators; e.g., real-time power grid simulators.


Integrating simulators
----------------------

#. Simulator self-description: Mosaik must provide a way for simulators do
   describe their capabilities, models, inputs, outputs, and so on. This
   self-description will later be used for creating scenarios.

#. Mosaik API: There must be an (easy and well documented) API that simulators
   can implement in order to communicate with mosaik.

#. :term:`Control strategies <control strategy>` (like multi-agent systems)
   should use the same API as simulators.


Scenario definition
-------------------

#. Defining scenarios should happen directly in Python to not introduce another
   technology that has to be maintained and because Python syntax is as easy as
   an arbitrary DSL.  Furthermore, Python is much more flexible and powerful
   than a simple DSL.

#. Connecting :term:`entities <entity>`: On the lowest level, mosaik must be
   able to connect two single entities. On a higher level, mosaik must be able
   to automatically connect two sets of entities based on their inputs and
   outputs. For example, PV modules with a *P* and *Q* output can be connected
   to power grid nodes with a *P* and *Q* input.

#. Filtering of entity sets: Mosaik must also offer means to automatically
   filter sets of entities based on their attributes or on existing connections
   to other entities.

#. Cyclic Data-flow Support: mosaik must offer a way to deal with cyclic data
   flows, e.g. between a controllable energy producer and a control strategy
   which generates schedules based on the current feed-in.

#. Physical Topology Access: mosaik must allow the :term:`control strategies
   <control strategy>` and :term:`simulators <simulator>` to query/traverse the
   physical topology created during the composition process.

#. Intra-Model Topology Access: a :term:`simulator` must offer the possibility
   to get access to the relations between the :term:`entities <entity>` of
   a :term:`model` (e.g., how nodes and lines in a power grid are
   interconnected) for building the complete physical topology.

#. Moving entities: Mosaik must support the specification of scenarios with
   moving resources like electric vehicles which may be connected to varying
   nodes in the power grid based on their current state.

#. Scenario variants: Mosaik must offer means to easily create scenario
   variants to e.g., simulate a scenario for summer and winter months.


Execution
---------

#. Mosaik must be able to report the progress of a simulation.

#. Data logging: mosaik must log data that is provided by the simulators
   for later evaluation. It must also be possible to filter what goes into
   the database when creating a scenario. Otherwise, the database might grow
   too large and contain mostly irrelevant data for the research question at
   hand.

#. It should be possible to distribute the simulator instances over multiple
   processes on the same machine and over multiple different machines or
   servers.

#. Mosaik should be usable as a library. That means, that the user who creates
   a scenario makes calls to mosaik's functionality to execute their scenario.
   This will allow them to easily test the scenario and hook into mosaik e.g.,
   for debugging purposes.

#. Mosaik should be able to run as a framework. That means that a mosaik
   process loads a scenario and executes a defined entry point (the scenario's
   *main* method). This allows to start a mosaik master process that manages
   the execution of multiple scenarios in parallel and that offers a weg GUI
   to monitor these simulations.

#. Configure log messages for every component independently: Simulation
   developers, scenario experts and mosaik core developers usually are
   interested in different kinds of debug output. It should thus be possible to
   change log levels for mosaik's various components independently.
