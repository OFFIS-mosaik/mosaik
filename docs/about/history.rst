=====================
The history of mosaik
=====================

Our work on mosaik started on July 15th, 2010 -- at least, the `initial
commit`__ happened on that day. Since then, we've come a long way …

__ https://bitbucket.org/mosaik/mosaik-legacy/commits/82aebc9a8d54fad3efd24ade4b28615873bee9ab


2.1 – 2014-10-24
================

- [NEW] Mosaik can now perform real-time simulations. Before, this
  functionality needed to be implemented by simulators. Now it’s just
  ``World.run(until=x, rt_factor=y)``, where ``rt_factor`` defines the
  simulation speed relative to the wall-clock time (`issue #24`).

- [NEW] Simulators can now expose extra methods via their API that can be
  called from a mosaik scenario. This allows you to, e.g., store static data in
  a data base. These extra API methods need to be specified in the simulator’s
  meta data (`issue #26`_).

- [NEW] ``util.connect_many_to_one()`` helper function.

- [NEW] More and better documentation:

  - Tutorial for integrating simulators, control strategies and for creating
    scenarios.

  - Sim API description

  - Scenario API description

  - Sim Manager documentation

  - Scheduler documentation

  - Discussion of design decisions

  - Logo, colors, CI

- [NEW] Added ``util.sync_call()`` which eases calling proxied methods of
  a simulator synchronously.

- [CHANGE] The *rel* attribute in the entity description returned by *create()*
  is now optional.

- [CHANGE] Moved proxied methods from ``SimProxy`` to ``SimProxy.proxy`` in
  order to avoid potential name clashes with other attributes.

- [CHANGE] Check a simulator’s models and extra API methods for potential name
  clashes with the built-in API methods.

- [CHANGE] The argument *execution_graph* of ``World`` was renamed to *debug*.
  The execution graph now also stores the time after a simulation step (in
  addition to the time before the step).

- [FIX] `issue #22`_: The asynchronous requests *get_data()* and *set_data()*
  now check if the ``async_requests`` flag was set in ``World.connect()``.

- [FIX] `issue #23`_: *finalize()* is now called for in-process Python
  simulators.

- [FIX] `issue #27`_: Dramatically improved simulation performance (30 times as
  fast in some cases) if simulators use different step sizes (e.g. 1 minute and
  1 hour) by improving some internal data structures.

.. _`issue #22`: https://bitbucket.org/mosaik/mosaik/issue/22/
.. _`issue #23`: https://bitbucket.org/mosaik/mosaik/issue/23/
.. _`issue #24`: https://bitbucket.org/mosaik/mosaik/issue/24/
.. _`issue #26`: https://bitbucket.org/mosaik/mosaik/issue/26/
.. _`issue #27`: https://bitbucket.org/mosaik/mosaik/issue/27/


2.0 – 2014-09-22
================

- [NEW] Updated documentation

- [CHANGE] Separated mosaik's package and API version. The former stays
  a string with a semantic version number; the later is now a simple integer
  (`issue #17`_).

- [CHANGE] Start/stop timeout for simulators was raised from 2 to 10 seconds.

- [CHANGE] Updated the mosaik logo. It now uses the flat colors and has some
  improved icon graphics.

- [CHANGE] Renamed ``mosaik.simulator`` to ``mosaik.scheduler``.

- [CHANGE] ``Entity`` and the World’s entity graph now store their simulator
  name.

- [FIX] `issue #16`_: Mosaik now always prints the name of the simulator if it
  closes its socket.

.. _`issue #16`: https://bitbucket.org/mosaik/mosaik/issue/16/
.. _`issue #17`: https://bitbucket.org/mosaik/mosaik/issue/17/


2.0a4 – 2014-07-31
==================

- [NEW] The model meta data may now contain the ``any_inputs`` which, if set
  to ``True``, allows any attribute to be connected to that model (useful for
  databases and alike).
- [CHANGE] The dictionary of input values in the API's ``step()`` call now
  also contains the source of a particular value. This is also usefull to for
  databases. This may break existing simulators.
- [CHANGE] "." is now used as separator in full entiy IDs instead of "/"
  (`issue #19`_).

.. _`issue #19`: https://bitbucket.org/mosaik/mosaik/issue/19/


2.0a3 – 2014-06-26
==================

- [NEW] Hierarchical entities: Entities can now have a list of child entities
  (`issue #14`_).
- [NEW] The ``World`` class now has a ``get_data()`` method that allows you to
  get data from entities while creating a scenario.
- [NEW] ``World.connect(a, b, ('X', 'X'))`` can now be simplified to
  ``World.connect(a, b, 'X')``.
- [NEW] Attribute ``Entity.full_id`` which uniquely identifies an entity:
  ``'<sid>/<eid>'``
- [NEW] Attribute ``ModelFactory.meta`` which is the meta data dictionary of
  a simulator.
- [NEW] ``World()`` now accepts a configuration dictionary which can, e.g.,
  specify the network address for mosaik.
- [NEW] Overview section for the docs
- [NEW] Description of the mosaik API in the docs
- [CHANGE] When you create entities, mosaik checks if the model parameters
  actually exists and raises an error if not (`issue #9`_).
- [CHANGE] The mosaik API’s ``init()`` function now receives the simulator ID
  as first argument (`issue #15`_).
- [CHANGE] The behavior of the ``get_related_entities()`` RPC that simulators
  can perform has been changed.
- [CHANGE] Various internal improvements
- [FIX] `issue #18`_. Improved the error message if a Python simulator could
  not be imported.
- [REMOVED] Attribute ``Entity.rel``.

.. _`issue #9`: https://bitbucket.org/mosaik/mosaik/issue/9/
.. _`issue #14`: https://bitbucket.org/mosaik/mosaik/issue/14/
.. _`issue #15`: https://bitbucket.org/mosaik/mosaik/issue/15/
.. _`issue #18`: https://bitbucket.org/mosaik/mosaik/issue/18/


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
