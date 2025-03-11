.. _glossary:

Glossary
========

.. glossary::

   Component API
      An outdated term for :term:`Simulator API <simulator api>`.

   Control strategy
      A program that is intended to observe and manipulate the state of
      objects (simulated or real) of a power system or those that are somehow
      connected to the power system; for example a multi-agent system that
      controls the feed-in of decentralized producers.

   Co-simulation
      In co-simulation the different subsystems which form a coupled problem
      are modeled and simulated in a distributed manner. The modeling is done
      on the subsystem level without having the coupled problem in mind. The
      coupled simulation is carried out by running the subsystems in a
      black-box manner. During the simulation the subsystems will exchange
      data. (source: `Wikipedia <http://en.wikipedia.org/wiki/Co-simulation>`_)

   Data-flow
      The exchange of data between two :term:`simulators <simulator>` or
      between the :term:`entities <entity>` of two simulators.

      Example: the (re)active power feed-in of a PV model that is sent to
      a node of a power system simulator.

   End-user API
      An outdated term for :term:`Scenario API <scenario api>`.

   Entity
      Represents an instance of a :term:`Model` within a mosaik
      :term:`simulation`.  Entities can be connected to establish a data-flow
      between them.  Examples are the nodes and lines of a power grid or single
      electric vehicles.

   Entity Set
      A set or list of :term:`entities <entity>`.

   Framework
      A software framework provides generic functionality that can be
      selectively changed and expanded by additional user-written code.

   Model
      A Model is a simplified representation of a real world object or system.
      It reproduces the relevant aspects of that object or system for its
      systematic analysis.

   mosaik API
      An outdated term for :term:`Simulator API <simulator api>`.

   Scenario
      Description of the system to be simulated. It includes the used
      :term:`models <model>` and their relations. It includes the state
      of the models and their data base. In the mosaik-context it includes also
      the :term:`simulators <simulator>`.

   Scenario API
      A Python-based API that enables the creation of simulation :term:`scenarios <scenario>`.
      It allows you to start :term:`simulators <simulator>`, instantiate models, and generate :term:`entity sets <entity set>`.
      Entities can be connected individually or in sets to establish data flows between simulators.

   Simulation
      The process of executing a scenario (and the simulation models).

   Simulation Model
      The representation of a :term:`model <model>` in programming code..

   Simulation time
      The "internal" time of the simulation, i.e., the time of the simulated world.
      In mosaik, this time is measured in steps starting from the start of the simulation.
      Conventionally, one step represents one second, but this can be adjusted by changing the ``time_resolution`` when creating a :class:`mosaik.World`.

   Simulator
      A program that contains the implementation of one or more
      :term:`simulation models <simulation model>` and is able to execute these
      models (that is, to perform a :term:`simulation`).

      Sometimes, the term *simulator* also refers all kinds of processes that
      can talk to mosaik, including actual simulators, control strategies,
      visualization servers, database adapters and so on.

   Simulator API
      Allows for the communication between :term:`simulators <simulator>` and mosaik.

   Sim-API
      An outdated term for :term:`Simulator API <simulator api>`.

   Smart Grid
      An electric power system that utilizes information exchange and control
      technologies, distributed computing and associated sensors and actuators,
      for purposes such as:

      - to integrate the behaviour and actions of the network users and other stakeholders,
      - to efficiently deliver sustainable, economic and secure electricity supplies.

      (source: `IEC <http://www.electropedia.org>`_)

   Step
      Mosaik executes simulators in discrete time steps. The step size of a
      time-based simulator can be an arbitrary integer. It can also vary
      during the simulation. Event-based simulators are stepped whenever its
      inputs are updated (by other simulators). They can also schedule steps
      for themselves.

      Mosaik uses integers for the representation of time (to avoid rounding
      errors etc.). It's unit (i.e. to how many seconds one integer step
      corresponds) can be defined in the scenario, and is passed to every
      simulation component via the :ref:`init function <api.init>` as key-word
      parameter *time_resolution. It's a floating point number and defaults to *1.*.

   Time resolution
      In mosaik, how many seconds correspond to mosaik :term:`step`.
      See the ``time_resolution`` argument of :class:`~mosaik.scenario.World` and :class:`~mosaik.async_scenario.AsyncWorld`.
