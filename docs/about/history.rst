=====================
The history of mosaik
=====================

Our work on mosaik started on July 15th, 2010 -- at least, the `initial
commit`__ happened on that day. Since then, we've come a long way …

__ https://bitbucket.org/mosaik/mosaik-legacy/commits/82aebc9a8d54fad3efd24ade4b28615873bee9ab


2.0a2 – 2014-05-05
==================

- [NEW] Preliminary documentation and installation instructions
  (https://mosaik.readthedocs.org)

- [NEW] Simulators can now set data to other simulators using the
  asynchronous request *set_data* (`issue #1`_).

- [NEW] There is now a start timeout for external processes (`issue #11`_).

- [CHANGE] Mosaik now raises an error if a simulator uses the wrong API version
  (`issue #4`_).

- [CHANGE] Mosaik prints everything to *stdout* instead of using the Python
  logging module (`issue #7`_).

- [FIX] `issue #2`_. Scheduling now works properly for processes using async.
  requests. New keyword argument *async_requests* for ``World.connect()``.

- [FIX] `issue #3`_. Local (in-process) Simulators can now also perform async.
  requests to mosaik (*get_progress*, *get_related_entities*, *get_data*,
  *set_data*).

- [FIX] `issue #8`_. Cleaned up the code a bit.

- [FIX] `issue #10`_. Tests for the sim manager improved.

.. _`issue #1`: https://bitbucket.org/mosaik/mosaik/issue/1/
.. _`issue #2`: https://bitbucket.org/mosaik/mosaik/issue/2/
.. _`issue #3`: https://bitbucket.org/mosaik/mosaik/issue/3/
.. _`issue #4`: https://bitbucket.org/mosaik/mosaik/issue/4/
.. _`issue #7`: https://bitbucket.org/mosaik/mosaik/issue/7/
.. _`issue #8`: https://bitbucket.org/mosaik/mosaik/issue/8/
.. _`issue #10`: https://bitbucket.org/mosaik/mosaik/issue/10/
.. _`issue #11`: https://bitbucket.org/mosaik/mosaik/issue/11/


2.0a1 – 2014-03-26
==================

- Mosaik 2 is a complete rewrite of mosaik 1 in order to improve its
  maintainability and flexibility. It is still an early alpha version and
  neither feature complete nor bug free.

- Removed features:

  - The *mosl* DSL (including Eclipse xtext and Java) are now gone. Mosaik now
    only uses Python.

  - Mosaik now longer has executables but is now used as a library.

  - The platform manager is gone.

  - Mosaik no longer includes a database.

  - Mosaik no longer includes a web UI.

- Mosaik now consists of four core components with the following feature sets:

  - mosaik API

    - The API has bean cleaned up and simplified.

    - Simulators and control strategies share the same API.

    - There are only four calls from mosaik to a simulator: *init*, *create*,
      *step* and *get_data*.

    - Simulators / processes can make asynchronous requests to mosaik during a
      step: *get_progress*, *get_related_entities*, *get_data*.

    - ZeroMQ with JSON is replaced by plain network sockets with JSON.

  - Scenarios:

    - Pure Python is now used to describe scenarios. This offers you more
      flexibility to create complex scenarios.

    - Scenario creation simplified: Start a simulator to get a model factory.
      Use the factory to create model instances (*entities*). Connect entities.
      Run simulation.

    - Connection rules are are no based on a primitive *connect* function that
      only connects two entities with each other. On top of that, any
      connection strategy can be implemented.

  - Simulation Manager:

    - Simulators written in Python 3 can be executed *in process*.

    - Simulators can be started as external processes.

    - Mosaik can connect to an already running instance of a simulator. This
      can be used as a replacement for the now gone platform manager.

  - Simulation execution:

    - The simulation is now event-based. No schedule and no synchronization
      points need to be computed.

    - Simulators can have different and varying step sizes.

- Mosaik ecosystem:

  - A high-level implementation of the mosaik 2 API currently only exists for
    Python. See https://bitbucket.org/mosaik/mosaik-api-python.

  - *mosaik-web* is a simple visualization for mosaik simulations. See
    https://bitbucket.org/mosaik/mosaik-web.

  - *mosaik-pypower* is an adapter for the *PYPOWER* load flow analysis
    library. See https://bitbucket.org/mosaik/mosaik-pypower and
    https://github.com/rwl/PYPOWER.

  - *mosaik-csv* and *mosaik-householdsim* are simple demo simulators that you
    can use to "simulate" CSV data sets and load-profile based households. See
    https://bitbucket.org/mosaik/mosaik-csv and
    https://bitbucket.org/mosaik/mosaik-householdsim.

  - There is a repository containing a simple demo scenario for mosaik. See
    https://bitbucket.org/mosaik/mosaik-demo.


1.1 – 2013-10-25
================

- [NEW] New API for control strategies.
- [NEW] Mosaik can be configured via environment variables.
- [NEW] Various changes and improvements implemented during Steffen’s
  dissertation.


1.0 – 2013-01-25
================

Mosaik 1 was nearly a complete rewrite of the previous version and already
incorporated many of the concepts and features described in Steffen Schütte's
`Phd thesis`__.

It used *mosl*, a DSL implemented with Eclipse and xtext, to describe
simulators and scenarios. Interprocess communication was done with ZeroMQ and
JSON encoded messages.

__ http://www.informatik.uni-oldenburg.de/download/Promotionen/dissertation_schuette_08012014.pdf


0.5 – 2011-08-22
================

This was the first actual version of mosaik that actually worked. However, the
simulators we were using at that time were hard coded into the simulation loop
and we used XML-RPC to communicate with the simulators.
