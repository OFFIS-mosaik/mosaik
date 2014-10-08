.. _glossary:

Glossary
========

.. glossary::

   Control strategy
      A program that is intended to observe and manipulate the state of
      objects (simulated or real) of a power system or those that are somehow
      connected to the power system; for example a multi-agent system that
      controls the feed-in of decentralized producers.

   Data-flow
      The exchange of data between two :term:`simulators <simulator>` or
      between the :term:`entities <entity>` of two simulators.

      Example: the (re)active power feed-in of a PV model that is sent to
      a node of a power system simulator.

   Entity
      Represents an instance of a :term:`Model` within a mosaik
      :term:`simulation`.  Entities can be connected to establish a data-flow
      between them.  Examples are the nodes and lines of a power grid or single
      electric vehicles.

   Entity Set
      A set or list of :term:`entities <entity>`.

   Model
      A synonym for :term:`simulation model`.

   Scenario
      Description of the system or situation to be simulated (with mosaik). The
      scenario describes, which :term:`simulators <simulator>` and
      :term:`models <model>` to instantiate and how to connect the resulting
      :term:`entities <entity>`.

   Simulation
      The process of executing a scenario (and the simulation models).

   Simulation Model
      An abstract representation of a system or description of the behavior of
      a system. This can either be in natural language (prosa and formulas) or
      in programm code.

   Simulator
      A program that contains the implementation of one or more
      :term:`simulation models <simulation model>` and is able to execute these
      models (that is, to perform a :term:`simulation`).

      Sometimes, the term *simulator* also refers all kinds of processes that
      can talk to mosaik, including actual simulators, control strategies,
      visualization servers, database adapters and so on.

   Step
      Mosaik executes simulators in discrete time steps. The step size of a
      simulator can be an arbitrary integer. It can also vary during the
      simulation.

      Mosaik does not dictate a unit for the simulation time and step size. The
      convention is to use seconds, but it is no problems if all simulators
      used minutes or milli seconds – as long as all of them assume the same
      unit.
