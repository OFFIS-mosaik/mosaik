===================
Scenario definition
===================

.. currentmodule:: mosaik.scenario

Modeling or composing a scenario in mosaik comprises three steps:

1. Starting simulators,

2. Instantiating models within the simulators, and

3. Connecting the model instances of different simulators to establish the data
   flow between them.

This page will show you how to create simple scenarios in these three steps.
It will also provide some recipes that allow you to create more complex
scenarios.

.. _scenario_definition:

The setup
=========

The central class for creating scenarios is :class:`mosaik.scenario.World` (for
your convenience, you can also import ``World`` directly from ``mosaik``). This
class stores all data and state that belongs to your scenario and its
simulation. It also provides various methods that allow you to start simulators
and establish the data flows between them.

In this tutorial, we'll create a very simple scenario using the example
simulation that is provided with the `Python implementation of the simulator
API`__.

__ https://gitlab.com/mosaik/mosaik-api-python/

We start by importing the :mod:`mosaik` package and creating
a :class:`World` instance:

.. code-block:: python

   >>> import mosaik
   >>> from mosaik.scenario import SimConfig
   >>>
   >>> sim_config: SimConfig = {
   ...     'ExampleSim': {'python': 'example_sim.mosaik:ExampleSim'},
   ... }
   >>>
   >>> world = mosaik.World(sim_config)

(You can leave off the type annotation on ``sim_config`` and the line importing
``SimConfig`` if you're not using type checking.)

As we start simulator instances by using *world*, it needs to know what
simulators are available and how to start them. This is called the *sim config*
and is a dict that contains every simulator we want to use together with some
information on how to start it.

In our case, the only simulator is the *ExampleSim*. It will be started by importing
the module ``example_sim.mosaik`` and instantiating the class ``ExampleSim``.
This is only possible with simulators written in Python 3. You can also let
mosaik start simulator as external processes or let it connect to already
running processes. The :doc:`simulator manager docs<simmanager>` explain how
this all works and give you some hints when to use which method of starting
a simulator.

In addition to the *sim config* you can optionally pass the *mosaik_config* dictionary to
:class:`World` in order to overwrite some general parameters for mosaik (e.g.,
the host and port number for its network socket or timeouts).  Usually, the
defaults work just well.

.. code-block:: python

   >>> world = mosaik.World(sim_config, mosaik_config={'addr': ('127.0.0.1', 5555), 'start_timeout': 10, 'stop_timeout': 10,})

.. _time_resolution:

Via the *time_resolution* parameter you can set a global time resolution for
the scenario, which will be passed to each simulator as keyword argument via
the init function (see :ref:`API init <api.init>`). It tells each simulator how to
translate mosaik's integer time to simulated time (in seconds from simulation
start). It has to be a float and it defaults to ``1.``.

.. code-block:: python

   >>> world = mosaik.World(sim_config, time_resolution=1.)

If you set the *debug* flag to ``True`` an execution graph will be created
during the simulation. This may be useful for debugging and testing. Note,
that this increases the memory consumption and simulation time.

.. code-block:: python

   >>> world = mosaik.World(sim_config, debug=False)

There are two more technical parameters: You can set the *cache* flag to False
if the average step size of the simulators is orders of magnitudes larger than
the time resolution, i.e. a time resolution of microseconds where the typical
step size is in the seconds range. This will considerably reduce the
simulation time.

.. code-block:: python

   >>> world = mosaik.World(sim_config, cache=True)

Via *max_loop_iterations* you can limit the maximum iteration count within one
time step for :ref:`same-time loops <same-time_loops>`. It's default value is 100.

.. code-block:: python

   >>> world = mosaik.World(sim_config, max_loop_iterations=100)

Starting simulators
===================

Now that the basic set-up is done, we can start our simulators:

.. code-block:: python

   >>> simulator_0 = world.start('ExampleSim', step_size=2)
   Starting "ExampleSim" as "ExampleSim-0" ...
   >>> simulator_1 = world.start('ExampleSim')
   Starting "ExampleSim" as "ExampleSim-1" ...

To start a simulator, we call :meth:`World.start()` and pass the name of the
simulator. Mosaik looks up that name in its *sim config*, starts the simulator
for us and returns a :class:`ModelFactory`. This factory allows us to
instantiate simulation models within that simulator.

In addition to the simulator name, you can pass further parameters for the
simulators. These parameters are passed to the simulator via the :ref:`init()
API call <api.init>`.


Instantiating simulation models
===============================

Simulators specify a set of public models in their meta data (see :ref:`init()
API call <api.init>`). These models can be accessed with the
:class:`ModelFactory` that :meth:`World.start()` returns as if they were normal
Python classes. So to create one instance of *ExampleSim's* model *A* we just
write:

.. code-block:: python

   >>> a = simulator_0.A(init_val=0)

This will create one instance of the *A* simulation model and pass the model
parameter ``init_val=0`` to it (see :ref:`create() API call <api.create>`).
Lets see what it is that gets returned to us:

.. code-block:: python

   >>> print(a)
   Entity('ExampleSim-0', '0.0', 'ExampleSim', A)
   >>> a.sid, a.eid, a.full_id
   ('ExampleSim-0', '0.0', 'ExampleSim-0.0.0')
   >>> a.sim_name, a.type
   ('ExampleSim', 'A')
   >>> a.children
   []

A model instances is represented in your scenario as an :class:`Entity`. The
entity belongs to the simulator *ExampleSim-0*, has the ID *0.0* and its type
is *A*. The entity ID is unique within a simulator. To make it globally unique,
we prepend it with the simulator ID. This is called the entity's *full ID* (see
:attr:`Entity.full_id`). You can also get a list of its child entities (which
is empty in this case).

In order to instantiate multiple instances of a model, you can either use
a simple list comprehension (or ``for`` loop) or call the static method
`create()` of the model:

.. code-block:: python

   >>> a_set = [simulator_0.A(init_val=i) for i in range(2)]
   >>> b_set = simulator_1.B.create(3, init_val=1)

The list comprehension is more verbose but allows you to pass individual
parameter values to each instance. Using ``create()`` is more concise but all
three instance will have the same value for *init_val*. In both cases you'll
get a list of entities (aka :term:`entity sets <entity set>`).


Setting initial events
======================

Time-based (and hybrid) simulators are automatically scheduled for time step 0,
and will organize their scheduling until the simulation's end themselves
afterward. For event-based simulators this is not the case, as they might only
want to be stepped if an event is created by another simulator for example.
Therefore you might need to set initial events for some event-based ones via
:meth:`World.set_initial_event()`, which sets an event for time 0 by default,
or at later times if explicitly stated:

.. code-block:: python

   >>> world.set_initial_event(a.sid)
   >>> world.set_initial_event(b.sid, time=3)


Connecting entities
===================

If we would now run our simulation, both, *simulator_0* and *simulator_1* would run
in parallel and never exchange any data. To change that, we need to connect
the models providing input data to entities requiring this data. In our case,
we will connect the *val_out* attribute of the *A* instances with the *val_in*
attribute of the *B* instances:

.. code-block:: python

   >>> a_set.insert(0, a)  # Put our first A instance to the others
   >>> for a, b in zip(a_set, b_set):
   ...     world.connect(a, b, ('val_out', 'val_in'))

The method :meth:`World.connect()` takes the source entity, the destination
entity and an arbitrary amount of *(source attribute, dest. attribute)* tuples.
If the name of the source attributes equals that of the destination attribute,
you can alternatively just pass a single string (e.g., ``connect(a, b,
'attr')``).

mosaik deals with two separate types of data exchange between simulators:

- First, there are measurements that have a value at each point of time.
  Examples include all kinds of physical measurements like the voltage at a
  grid node or the power output of a PV system.
- Second, there are events (those were introduced in mosaik 3) which happen at
  a particular point in time. A typical example is a message between ICT devices
  or a set-point message from some controller to the PV system that it controls.

Each attribute of a mosaik simulator can deal either with measurements or with
events. In case of time-based simulators, all attributes work as measurements,
in case of event-based simulators, all attributes work as events. Hybrid-simulators
can work with either on an attribute-by-attribute basis (i.e. each attribute is
either for measurements or for events). For historic reasons, input attributes
are called trigger attributes when they deal with events, and output attributes
are called non-persistent when they deal with events. The opposite terms ‘non-trigger’
and ‘persistent’ are used for measurement attributes (input and output, respectively).

mosaik will complain if you connect a non-persistent output to a non-trigger
input. This is because the target simulator should be able to rely on always
receiving input on its non-trigger attributes, but just delaying or even repeating
the last event would be semantically unsound (the event is associated with the
time at which it was generated by the source simulator, not with the time at which
the target simulator happens to run).

.. figure:: /_static/connect_attr_simulator.*
   :width: 600
   :align: center
   :alt: Solutions to solve warnings for attribute connections

   A non-persistent output connected to a non-trigger input leads to a warning.

Usually, the solution to resolve this warning is to change the type of one of the
affected attributes: the source attribute from non-persistent to persistent, or
the target attribute from non-trigger to trigger. You can do this without
affecting the simulator’s other attributes by changing the simulator’s type to
hybrid, where you can then specify which attributes should be trigger and/or
non-persistent. :ref:`(See here for the format of META.) <meta>`
Note that the attributes of hybrid simulator behave like measurements by default,
so if you are changing an event-based simulator to hybrid, you will have to specify
all attributes except for the affected one to be trigger and/or non-persistent if
you want to preserve their previous behavior.

We also encourage you to carefully think about the case where you attempt to
connect a persistent output to a trigger input. However, because there is the
common case of saving data generated in the simulation using some database or
writer simulator (regardless of how whether it is an event or a measurement),
mosaik will not complain when you set up connections like this.

You can only connect entities that belong to different simulators with each
other (that's why we created two instances of the *ExampleSim*).

You are also not allowed to create circular dependencies via standard
connections only (e.g., connect *a* to *b* and then connect *b* to *a*).
There are several ways to allow a bidirectional or cyclic exchange of data,
which is required for things like control strategies, e.g. via *time-shifted*
or *weak* connections. See section :ref:`cyclic_data-flows` for details.


.. _running-the-simulation:

Running the simulation
======================

When all simulators are started, models are instantiated and connected, we can
finally run our simulation:

.. code-block:: python

   >>> world.run(until=10)  # doctest: +SKIP
   Starting simulation.
   Simulation finished successfully.

This will execute the simulation from time 0 until we reach the time *until*
(in simulated time units). The :doc:`scheduler section <scheduler>` explains in
detail what happens when you call ``run()``.

While the simulation is running, the current progress is visualized using a
`tqdm <https://pypi.org/project/tqdm/>`_ progress bar. You can turn this off
using the `print_progress` parameter of `world.run`:

.. code-block:: python

   world.run(until=10, print_progress=False)

If you want a more detailed progress report, you can also set
``print_progress='individual'`` which will produce a separate progress bar for
each simulator in your simulation.

We can also set the *lazy_stepping* flag (default: ``True``). If
``True``, a simulator can only run ahead one step of its successors. If
``False``, a simulator always steps as long as all inputs are provided. This
might decrease the simulation time but increase the memory consumption.

.. code-block:: python

   >>> world.run(until=END, lazy_stepping=False)

To wrap it all up, this is how our small example scenario finally looks like:

.. code-block:: python

   # Setup
   import mosaik

   sim_config = {
       'ExampleSim': {'python': 'example_sim.mosaik:ExampleSim'},
   }

   world = mosaik.World(sim_config)

   # Start simulators
   simulator_0 = world.start('ExampleSim', step_size=2)
   simulator_1 = world.start('ExampleSim')

   # Instantiate models
   a_set = [simulator_0.A(init_val=i) for i in range(3)]
   b_set = simulator_1.B.create(3, init_val=1)

   # Connect entities
   for a, b in zip(a_set, b_set):
       world.connect(a, b, ('val_out', 'val_in'))

   # Run simulation
   world.run(until=10)


.. _cyclic_data-flows:

How to achieve cyclic data-flows
========================================

Bi-directional (or cyclic) data-flows can occur easily in many scenarios,
e.g. when you want to integrate control strategies. In this case you have to
explicitly define in which order the simulators have to be stepped in case they
are scheduled at the same time step simultaneously. Otherwise the simulation would
get stuck in a dead-lock. Therefore this trivial approach is not allowed in mosaik:

.. code-block:: python

   # Send battery's active power value to the controller
   world.connect(battery, controller, 'P')
   # Controller sends back a schedule to the battery
   world.connect(controller, battery, 'schedule')

The problem with this is that mosaik cannot know whether to compute *battery.P*
or *controller.schedule* first.

There are different ways to solve this problem, depending of the stepping type
of your simulators:

Time-based
----------
For time-based simulators the easiest way is to indicate explicitly that the
output of at least one simulator (e.g. the schedule of the controller)is to be
used for time steps afterwards (here by the battery) via the *time_shifted*
flag:

.. code-block:: python

   world.connect(battery, controller, 'P')
   world.connect(controller, battery, 'schedule', time_shifted=True,
                 initial_data={'schedule': initial_schedule})

As for the first step this data cannot be provided yet, you have to set it via
the *initial_data* argument. This example would result in a sequential execution
of the two simulators. If you set the time_shifted flag for both connections, you
get a parallel execution.

The other option to resolve the cycle is to use asynchronous requests. For this you
only connect the battery's *P* to the controller and let the control strategy set the
new schedule via the asynchronous request :ref:`rpc.set_data`. To indicate
this in your scenario, you set the
*async_request* flag of :meth:`World.connect()` to ``True``:

.. code-block:: python

   world.connect(battery, controller, 'P', async_requests=True)

This way, mosaik will push the value for *P* from the battery to the
controller. It will then wait until the controller's :ref:`step <api.step>` is
done before the next step for the battery will be computed.

The advantage of this approach is that the call of set_data is optional, so
you don't need to send a schedule on every step if there's no new schedule.
The disadvantage is that you have to implement the set_data call within the
simulator with the specific destination, making it less modular.

The *step* implementation of the controller could roughly look like this:

.. code-block:: python

   class Controller(Simulator):

       def step(self, t, inputs):
          schedule = self._get_schedule(inputs)
          yield self.mosaik.set_data(schedule)
          return t + self.step_size

Event-based
-----------
For cyclic dependencies of event-based simulators you have to set one (and
only one) connection to *weak*, analogous to the *time_shifted* connections.
This allows mosaik to create a topological ranking of the simulators which is
used to resolve eventual deadlocks (when two or more simulators have scheduled
steps at the same time). In contrast to the time-shifted connections, weakly
connected output can also be valid/used at the same point in time. This
enables algebraic loops within one time step for example. You just have to
make sure that you don't construct infinite loops. See section
:ref:`Same-time Loops <same-time_loops>` for details.

How to filter entity sets
=========================

When you create large-scale scenarios, you often work with large sets of
entities rather than single ones. This section provides some examples how you
can extract a sub-set of entities from a larger entity set based on arbitrary
criteria.

Let's assume that we have created a power grid with `mosaik-pypower`__:

.. code-block:: python

   grid = pypower.Grid(gridfile='data/grid.json').children

Since mosaik-pypower's *Grid* entity only serves as a container for the buses
and branches of our power grid, we directly bound its *children* to the name
``grid``. So *grid* is now a list containing a *RefBus* entity and multiple
*Transformer*, *PQBus* and *Branch* entities.

So how do we get a list of all transformers? This way:

.. code-block:: python

   transformers = [e for e in grid if e.type == 'Transformer']

How do we get the single *RefBus*? This way:

.. code-block:: python

   refbus = [e for e in grid if e.type == 'RefBus'][0]

Our *PQBus* entities are named like *Busbar_<i>* and *ConnectionPoint_<i>* to
indicate to which buses we can connect consumers and producers and to which we
shouldn't connect anything. How do we get a list of all *ConnectionPoint*
buses? We might be tempted to do it this way:

.. code-block:: python

   conpoints = [e for e in grid if e.eid.startswith('ConnectionPoint_')]

The problem in this particular case is, that *mosaik-pypower* prepends a "grid
ID" to each entity ID, because it can handle multiple grid instances at once.
So our entity IDs are actually looking like this:
*<grid_idx>-ConnectionPoint_<i>*.  Using regular expressions, we can get our
list:

.. code-block:: python

   import re

   regex_conpoint = re.compile(r'\d+-ConnectionPoint_\d+')

   conpoints = [e for e in grid if regex_conpoint.match(e.eid)]

If we want to connect certain consumers or producers to defined nodes in our
grid (e.g., your boss says: "This PV module needs to be connected to
*ConnectionPoint_23*!"), creating a dict instead of a list is a good idea:

.. code-block:: python

   remove_grididx = lambda e: e.eid.split('-', 1)[1]  # Little helper function
   cps_by_name = {remove_grididx(e): e for e in grid if regex_conpoint.match(e)}

This will create a mapping where the string ``'ConnectionPoint_23'`` maps to
the corresponding ``Entity`` instance.

This was just a small selection of how you can filter entity sets using
list/dict comprehensions. Alternatively, you can also use the :func:`filter()`
function or a normal ``for`` loop. You should also take at look at the
:mod:`itertools` and :mod:`functools` modules. You'll find even more
functionality in specialized packages like `PyToolz`__.

__ https://pypi.python.org/pypi/mosaik-pypower
__ http://toolz.readthedocs.org/en/latest/index.html


How to create user-defined connection rules
===========================================

The method :meth:`World.connect()` allows you to only connect one pair of
entities with each other. When you work with larger entity sets, you might not
want to connect every entity manually, but use functions that take to sets of
entities and connect them with each other based on some criteria.

The most common case is that you want to randomly connect the entities of one
set to another, for example, when you distribute a number of PV modules over a
power grid.

For this use case, mosaik provides :func:`mosaik.util.connect_randomly()`. It
takes two sets and connects them either evenly or purely randomly:

.. code-block:: python

   world = mosaik.World(sim_config)

   grid = pypower.Grid(gridfile=GRID_FILE).children
   pq_buses = [e for e in grid if e.type == 'PQBus']
   pvs = pvsim.PV.create(20)

   # Assuming that len(pvs) < len(pq_buses), this will
   # connect 0 or 1 PV module to each bus:
   mosaik.util.connect_randomly(world, pvs, pq_buses, 'P')

   # This will distribute the PV modules purely randomly, but every
   # bus will have at most 3 modules connected to it.
   mosaik.util.connect_randomly(world, pvs, pq_buses, 'P',
                                 evenly=False, max_connects=3)

Another relatively common use case is connecting a set of entities to one other
entity, e.g., when you want to connect a number of controllable energy
producers to a central scheduler. For this use case, mosaik provides
:func:`mosaik.util.connect_many_to_one()`

.. code-block:: python

   ...
   pvs = pvsim.PV.create(30)
   chps = chpsim.CHP.create(20)
   controller = cs.Scheduler()

   # Connect all producers to the controller, remember to set the
   # "async_requests" flag.
   connect_many_to_one(world, chain(pvs, chps), controller, 'P',
                       async_requests=True)

Connection rules are oftentimes highly specific for a project.
:func:`~mosaik.util.connect_randomly()` and
:func:`~mosaik.util.connect_many_to_one()` are currently the only functions that
are useful and complicated enough to ship it with mosaik. But writing your own
connection method is not that hard, as you can see in the
``connect_many_to_one`` example:

.. code-block:: python

   from itertools import chain

   def connect_many_to_one(world, src_set, dest_entity, *attrs,
                           async_requests=False):
       for src_entity in src_set:
           world.connect(src_entity, dest_entity, *attrs,
                         async_requests=async_requests)


How to retrieve static data from entities
=========================================

Sometimes, the entities don't contain all the information that you need in
order to decide which entity connect to which, but your simulation model could
provide that data. An example for this might be the maximum amount of active
power that a producer is able to produce.

Mosaik allows you to query a simulator for that data during composition time
via :meth:`World.get_data()`:

.. code-block:: python

   >>> example_simulator = world.start('ExampleSim')
   Starting "ExampleSim" as "ExampleSim-2" ...
   >>> entities = example_simulator.A.create(3, init_val=42)
   >>> data = world.get_data(entities, 'val_out')
   >>> data[entities[0]]
   {'val_out': 42}

The entities that you pass to this function don't need to belong to the same
simulator (instance) as long as they all can provide the required attributes.


How to access topology and data-flow information
================================================

The :class:`World` contains two `networkx Graphs
<https://networkx.github.io/documentation/latest/>`_ which hold
information about the data-flows between simulators and the simulation topology
that you created in your scenario. You can use these graphs, for example, to
export the simulation topology that mosaik created into a custom data or file
format.

:attr:`World.df_graph` is the directed *dataflow graph* for your scenarios. It
contains a node for every simulator that you started. The simulator ID is used
to label the nodes. If you established a data-flow between two simulators (by
connecting at least two of their entities), a directed edge between two nodes
is inserted.  The edges contain a list of the data-flows as well as the
*async_requests*, *time_shifted*, and *weak* flags
(see :ref:`cyclic_data-flows`) and the *trigger* and *pred_waiting* flags.

The data-flow graph may, for example, look like this:

.. code-block:: python

   world.df_graph.node == {
       'PvSim-0': {},
       'PyPower-0': {},
   }
   world.df_graph.edge == {
       'PvSim-0': {'PyPower-0': {
           'async_requests': False,
           'dataflows': [
               ('PV_0', 'bus_0', ('P_out', 'P'), ('Q_out', 'Q')),
               ('PV_1', 'bus_1', ('P_out', 'P'), ('Q_out', 'Q')),
            ],
       }},
   }

:attr:`World.entity_graph` is the undirected *entity graph*. It contains a node
for every entity. The full entity ID (``'sim_id.entity_id'``) is used as node
label.  Every node also stores the simulator name and entity type. An edge
between two entities is inserted

* if they are somehow related within a simulator (e.g., a PyPower branch is
  related to the two PyPower buses to which it is adjacent) (see
  :ref:`api.create`); or

* if they are connected via :meth:`World.connect()`.

The entity graph may, for example, look like this:

.. code-block:: python

    world.entity_graph.node == {
        'PvSim_0.PV_0': {'sim': 'PvSim', 'type': 'PV'},
        'PvSim_0.PV_1': {'sim': 'PvSim', 'type': 'PV'},
        'PyPower_0.branch_0': {'sim': 'PyPower', 'type': 'Branch'},
        'PyPower_0.bus_0': {'sim': 'PyPower', 'type': 'PQBus'},
        'PyPower_0.bus_1': {'sim': 'PyPower', 'type': 'PQBus'},
    }
    world.entity_graph.edge == {
        'PvSim_0.PV_0': {'PyPower_0.bus_0': {}},
        'PvSim_0.PV_1': {'PyPower_0.bus_1': {}},
        'PyPower_0.branch_0': {'PyPower_0.bus_0': {}, 'PyPower_0.bus_1': {}},
        'PyPower_0.bus_0': {'PvSim_0.PV_0': {}, 'PyPower_0.branch_0': {}},
        'PyPower_0.bus_1': {'PvSim_0.PV_1': {}, 'PyPower_0.branch_0': {}},
    }

The :ref:`rpc.get_related_entities` API call also uses and returns (parts of)
the entity graph. So you can access it in your scenario definition as well as
from with a simulator, control strategy or monitoring tool.

Please consult the `networkx documentation
<http://networkx.github.io/documentation/latest/>`_ for more details about
working with graphs and directed graphs.


How to destroy a world
======================

When you are done working with a world, you should shut it down properly:

.. code-block:: python

   >>> world.shutdown()

This will, for instance, close mosaik's socket and allows new ``World``
instances to reuse the same port again.

:meth:`World.run()` automatically calls :meth:`World.shutdown()` for you.


How to do real-time simulations
===============================

It is very easy to do real-time (or "wall-clock time") simulations in mosaik.
You just pass an *rt_factor* to :meth:`World.run()` to enable it:

.. code-block:: python

   world.run(until=10, rt_factor=1)

A real-time factor of 1 means, that 1 simulation time unit (usually
a simulation second) takes 1 second of real time. Thus, if you set the
real-time factor to 0.5, the simulation will run twice as fast as the real
time. If you set it to 1/60, one simulated minute will take one real-time
second.

It may happen that the simulators are too slow for the real-time factor chosen.
That means, they take longer than, e.g., one second to compute a step when
a real-time factor of one second is set. If this happens, mosaik will by
default just print a warning message to stdout. However, you can also let your
simulation crash in this case by setting the parameter *rt_strict* to ``True``.
Mosaik will then raise a :exc:`RuntimeError` if your simulation is too slow:

.. code-block:: python

   world.run(until=10, rt_factor=1/60, rt_strict=True)


How to call extra methods of a simulator
========================================

A simulator may optionally define additional API methods (see :ref:`api.init`)
that you can call from your scenario. These methods can implement operations,
like setting some static data to a simulator, which don't really fit into
``init()`` or ``create()``.

These methods are exposed via the model factory that you get when you start
a simulator. In the following example, we'll call the ``example_method()``
that the example simulator shipped with the mosaik Python API:

.. code-block:: python

   >>> world = mosaik.World({'ExampleSim': {
   ...     'python': 'example_sim.mosaik:ExampleSim'}})
   >>> es = world.start('ExampleSim')
   Starting "ExampleSim" as "ExampleSim-0" ...
   >>>
   >>> # Now brace yourself ...
   >>> es.example_method(23)
   23
   >>>
   >>> world.shutdown()
