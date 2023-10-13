=====================
The history of mosaik
=====================

Our work on mosaik started on July 15th, 2010 -- at least, the initial
commit happened on that day. Since then, we've come a long way …

3.2.0 - 2023-08-31
------------------
- [NEW] Visualizations for the simulation debug information (https://gitlab.com/mosaik/mosaik/-/issues/173)
- [NEW] Allow to open a new console for simulator (https://gitlab.com/mosaik/mosaik/-/issues/84)
- [FIX] Lift restriction of only one weak connection per cycle (https://gitlab.com/mosaik/mosaik/-/issues/151)
- [FIX] Incorrect triggering when adding several edges (https://gitlab.com/mosaik/mosaik/-/issues/92)
- [IMPROVEMENT] Switch from simpy to asycnio (https://gitlab.com/mosaik/mosaik/-/issues/103)
- [CHANGE] Removed support for Python 3.7, added support for Python 3.11 (https://gitlab.com/mosaik/mosaik/-/issues/171)

3.1.1 - 2023-01-11
------------------

- [FIX] Fix compatibilty with mosaik 2 simulators (https://gitlab.com/mosaik/mosaik/-/issues/152)

3.1.0 - 2022-11-23
------------------
- [NEW] Add progress bar to visualize simulation progress (https://gitlab.com/mosaik/mosaik/-/merge_requests/58)
- [NEW] Add type annotations (https://gitlab.com/mosaik/mosaik/-/issues/107)
- [NEW] Add proper logging (https://gitlab.com/mosaik/mosaik/-/issues/98)
- [DEPRECATED] Deprecated tags for set_data und async_requests (https://gitlab.com/mosaik/mosaik/-/issues/102)
- [CHANGE] Improved benchmarks with new result table (https://gitlab.com/mosaik/mosaik/-/issues/94)
- [FIX] Unexpected behavior of (time-based) simulators whose output is not used anymore (https://gitlab.com/mosaik/mosaik/-/issues/90)
- [FIX] Lazy stepping does not work (https://gitlab.com/mosaik/mosaik/-/issues/89)
- [FIX] Negative max_advance values in same time loop (https://gitlab.com/mosaik/mosaik/-/issues/82)
- [FIX] Initial data for time-shifted connection for hybrid simulator (https://gitlab.com/mosaik/mosaik/-/issues/81)
- [FIX] Bug related to None value for "dest_sim.next_step" in particular connection structure (https://gitlab.com/mosaik/mosaik/-/issues/80)

3.0.2 - 2022-06-01
------------------

- [CHANGE] Updated mosaik-api version to 3.0.2

3.0.1 - 2022-05-02
------------------

- [CHANGE] Set external events via highlevel function call
- [FIX] Allow PATCH version to be included in the mosaik-api version format

3.0.0 - 2021-06-07
------------------

- This is a major upgrade to improve the discrete-event capabilities. Simulators' steps
  can now also be triggered by the output of other simulators.

- [NEW] Native support of discrete-event simulations
- [NEW] A global time resolution can be set for the scenario.
- [NEW] Simulators can request steps asynchronously via *set_event()* to react to external events.
- [NEW] Ability to specify output data as non-persistent (i.e. transient)
- [CHANGE] New api 3:
  - Simulators have now a *type* ('time-based'|'event-based'|'hybrid').
  - *time_resolution* is passed as argument of the *init* function.
  - *max_advance* is passed as argument of the *step* function.
- [CHANGE] Update of the documentation

2.6.1 - 2021-06-04
------------------

- [CHANGE] Updated ReadTheDocs to support versioning
- [CHANGE] Updated setup: mosaik-api>=2.3,<3
- [CHANGE] Updated networkx version to 2.5

2.6.0 - 2020-05-08
==================

- [NEW] The print of the simulation progress is now optional and can be disabled via a flag
  world.run(END, print_progress=False).
- [NEW] Additional starters can now be added via external packages (the standard ones are
  'python', 'cmd', and 'connect').

2.5.3 - 2020-04-30
==================

- [FIX] Constrain simpy version to <4.0.0 due to simpy.io incompatibility
- [CHANGE] Updated Odysseus tutorial
- [CHANGE] Eliminated shifted_cache which reduces memory consumption

2.5.2 - 2019-11-01
==================

- [NEW] Special characters are now allowed in path names
- [NEW] Compatible to the new versions of networkx
- [CHANGE] python 3.6, 3.7 and 3.8 are currently supported, python 3.4 and 3.5 not anymore.
- [FIX] Various minor internal changes
- [FIX] Various documentation updates and fixes

2.5.1 - 2018-11-29
==================

- [NEW] When calling the world.start() command for a simulator, users can now set a predefined
  value for the posix flag (e.g. True) to prevent automatic detection of the operating system.
  This facilitates the creation of some co-simulation cases across OS (e.g. Windows and Linux).

2.5.0 - 2018-09-05
==================

- [NEW] Connection option "time_shifted" added as alternative to async_requests. This will
  make creating cyclic data dependencies between simulators more usable since usage of
  set_data with an API implementation will no longer be needed.

2.4.0 - 2017-12-06
==================

- [NEW] Compatible to the new versions of networkx, simpy and simpy.io
- [CHANGE] python 3.4, 3.5 and 3.6 are currently supported python 3.3 is no longer supported
- [FIX] Various bug fixes

2.3.0 - 2016-04-26
==================
- [NEW] Allow passing environment vars to sup processes
- [FIX] Fixed a bug in the version validation which raised an error when using
  a floating point for the version

2.2.0 - 2016-02-15
==================

- [NEW] API version 2.2: Added an optional "setup_done()" method.

- [CHANGE] API version validation: The API version is no longer an integer but
  a "major.minor" string.  The *major* part has to math with mosaiks major
  version.  The *minor* part may be lower or equal to mosaik's minor version.

- [FIX] Various minor fixes and stability improvements.

- [FIX] Various docuentation updates and fixes.


2.1 – 2014-10-24
================

- [NEW] Mosaik can now perform real-time simulations. Before, this
  functionality needed to be implemented by simulators. Now it’s just
  ``World.run(until=x, rt_factor=y)``, where ``rt_factor`` defines the
  simulation speed relative to the wall-clock time (issue #24).

- [NEW] Simulators can now expose extra methods via their API that can be
  called from a mosaik scenario. This allows you to, e.g., store static data in
  a data base. These extra API methods need to be specified in the simulator’s
  meta data (issue #26).

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

- [FIX] issue #22: The asynchronous requests *get_data()* and *set_data()*
  now check if the ``async_requests`` flag was set in ``World.connect()``.

- [FIX] issue #23: *finalize()* is now called for in-process Python
  simulators.

- [FIX] issue #27: Dramatically improved simulation performance (30 times as
  fast in some cases) if simulators use different step sizes (e.g. 1 minute and
  1 hour) by improving some internal data structures.


2.0 – 2014-09-22
================

- [NEW] Updated documentation

- [CHANGE] Separated mosaik's package and API version. The former stays
  a string with a semantic version number; the later is now a simple integer
  (issue #17).

- [CHANGE] Start/stop timeout for simulators was raised from 2 to 10 seconds.

- [CHANGE] Updated the mosaik logo. It now uses the flat colors and has some
  improved icon graphics.

- [CHANGE] Renamed ``mosaik.simulator`` to ``mosaik.scheduler``.

- [CHANGE] ``Entity`` and the World’s entity graph now store their simulator
  name.

- [FIX] issue #16: Mosaik now always prints the name of the simulator if it
  closes its socket.


2.0a4 – 2014-07-31
==================

- [NEW] The model meta data may now contain the ``any_inputs`` which, if set
  to ``True``, allows any attribute to be connected to that model (useful for
  databases and alike).
- [CHANGE] The dictionary of input values in the API's ``step()`` call now
  also contains the source of a particular value. This is also usefull to for
  databases. This may break existing simulators.
- [CHANGE] "." is now used as separator in full entiy IDs instead of "/"
  (issue #19).


2.0a3 – 2014-06-26
==================

- [NEW] Hierarchical entities: Entities can now have a list of child entities
  (issue #14).
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
  actually exists and raises an error if not (issue #9).
- [CHANGE] The mosaik API’s ``init()`` function now receives the simulator ID
  as first argument (issue #15).
- [CHANGE] The behavior of the ``get_related_entities()`` RPC that simulators
  can perform has been changed.
- [CHANGE] Various internal improvements
- [FIX] issue #18. Improved the error message if a Python simulator could
  not be imported.
- [REMOVED] Attribute ``Entity.rel``.


2.0a2 – 2014-05-05
==================

- [NEW] Preliminary documentation and installation instructions
  (https://mosaik.readthedocs.org)

- [NEW] Simulators can now set data to other simulators using the
  asynchronous request *set_data* (issue #1).

- [NEW] There is now a start timeout for external processes (issue #11).

- [CHANGE] Mosaik now raises an error if a simulator uses the wrong API version
  (issue #4).

- [CHANGE] Mosaik prints everything to *stdout* instead of using the Python
  logging module (issue #7).

- [FIX] issue #2. Scheduling now works properly for processes using async.
  requests. New keyword argument *async_requests* for ``World.connect()``.

- [FIX] issue #3. Local (in-process) Simulators can now also perform async.
  requests to mosaik (*get_progress*, *get_related_entities*, *get_data*,
  *set_data*).

- [FIX] issue #8. Cleaned up the code a bit.

- [FIX] issue #10. Tests for the sim manager improved.


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
    Python. See https://gitlab.com/mosaik/mosaik-api-python.

  - *mosaik-web* is a simple visualization for mosaik simulations. See
    https://gitlab.com/mosaik/mosaik-web.

  - *mosaik-pypower* is an adapter for the *PYPOWER* load flow analysis
    library. See https://gitlab.com/mosaik/mosaik-pypower and
    https://github.com/rwl/PYPOWER.

  - *mosaik-csv* and *mosaik-householdsim* are simple demo simulators that you
    can use to "simulate" CSV data sets and load-profile based households. See
    https://gitlab.com/mosaik/mosaik-csv and
    https://gitlab.com/mosaik/mosaik-householdsim.

  - There is a repository containing a simple demo scenario for mosaik. See
    https://gitlab.com/mosaik/mosaik-demo.


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
