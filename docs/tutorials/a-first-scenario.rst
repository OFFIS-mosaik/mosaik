================
A first scenario
================

For our first scenario, we will couple a fake weather simulator (just creating random values) with a simulator for photovoltaic (PV) systems.
We will connect these PV systems to a power grid simulation and observe the effects at the node in our grid that is connected to the external grid.

Installation
============

The first step after installing mosaik itself is to install the packages necessary for our simulation.
We will be using ``mosaik-pandapower-2`` and ``mosaik-pv``.
Both of them are on PyPI, so you can install them using your favorite way of managing Python packages (``pip install`` in your virtual environment, your editor's Python package management, etc.).
We will also use mosaik's built-in function simulator as a fake weather simulator and the built-in output simulator to see what's going on.

Sic mundus creatus est
======================

Every mosaik scenario has its humble beginnings in importing mosaik.
We will also be using Python's ``random`` module, a function from ``mosaik.util`` and Python's built-in pretty printer.

.. literalinclude:: code/scenario_1.py
   :start-at: import mosaik
   :end-before: # end

We then need to set up a dict that describes all the simulators that we intend to use in our simulation and how to start or connect to them.
This dict is conventionally called ``SIM_CONFIG``.
For our scenario, it will look like this:

.. literalinclude:: code/scenario_1.py
   :start-at: SIM_CONFIG:
   :end-before: # end

Each entry in ``SIM_CONFIG`` describes one type of simulator.
The key (like ``"Weather"`` and ``"Grid"``) can be freely chosen by you, the scenario author.
The value is yet another dictionary that describes how to connect to this type of simulator.
For now, we are only using the ``"python"`` method, which will run the simulator in the same Python process as your scenario.
In this case, the dictionary has a single key ``"python"`` that specifies the module path and the name of a subclass of ``mosaik_api_v3:Simulator``, separated by a colon.
The documentation of the simulator that you are using should contain this information.

.. admonition:: On module paths

   The very basic input and output simulators that included in mosaik can be found in the ``mosaik.basic_simulators`` module.
   The default path for other simulators that are maintained by the mosaik team is ``mosaik_components.<name_of_the_component>``, though many of them are still in other locations for legacy reasons.
   Simulators written by you or others can be stored wherever the author prefers, though we kindly ask not to publish them in the ``mosaik_components`` namespace.

.. admonition:: On type annotations

   mosaik comes with support for type annotations, see for example the ``mosaik.SimConfig`` in the snippet above.
   You can just leave them off if you prefer, but if you turn on your Python type checker, they will often be able to tell you when you accidentally put a typo in your data structures.

We are now ready to create the world.
This won’t take seven days, just

.. literalinclude:: code/scenario_1.py
   :start-at: world =
   :end-at: world =

Using this ``world``, we can start our simulators:

.. literalinclude:: code/scenario_1.py
   :start-after: # start simulators
   :end-before: # end

The first argument to a call to ``world.start`` is one of the simulator names specified in the ``SIM_CONFIG``.
Then, you can optionally specify the ID your simulator should have in the scenario using the ``sim_id`` keyword argument.
If you don't specify the simulator ID, it will be derived from the simulator name automatically.
For example, the output simulator will be called *Output-0*.
The ``sim_id`` and all further keyword arguments will also be passed on to the simulator.
The simulator's documentation will contain details about which further arguments are supported.
In our case, we specify ``step_size=900`` for all simulators except the output simulator.

.. note::

   This step size is a common convention in mosaik as 900 seconds correspond to 15 minutes, which is the market interval on many energy markets.

The output simulator does not need to know the step size because it is “event-based”, which means that it will run automatically whenever it receives input.
We will discuss the distinction between the simulator types further in TODO.

In our scenario, we have created one instance of each simulator.
It is possible to create multiple instances of the same simulator by calling ``world.start`` with the same simulator name multiple times.
However, if the simulator supports it, it is usually better to create multiple entities within a single simulator instance, instead.
Entities are the subject of the next section.

Creating entities
=================

Having started our simulators, we now need to create entities in them.

.. admonition:: What are entities?	

   In co-simulations it is very common to want to simulate many copies each of only a few types of things, for example a number of PV systems which are each described by the same formulas (but with different parameters).
   In the context of mosaik, we call these types *models* and each copy of them an *entity*.
   If you are familiar with class-based object-oriented programming languages like Python or Java, a model is like a class and an entity is like an object.
   (Technically, this is always true, regardless of whether you are familiar with object orientation or not.)

   Each simulator may offer several different models and will usually allow you to create as many entities of each model as you need.
   All entities created in one simulator will run at the same time during the simulation, but each may work with different inputs and produce its own output.
   The role of the entity's model is to describe how the input to (and output of) the entity must be structured.

   We use entities because having one simulator calculate multiple similar things at once is usually more efficient than starting a whole new instance of the simulator for each thing.
   We recommend that you only start several instances of a simulator when you need it to run at multiple points within the same time step or when the simulator does not support multiple entities.

Our highly realistic weather model will be based on random values provided by the built-in input simulator.
In our example, we will assume that all PV systems are close enough together that they are governed by the same weather.
We therefore only need one wheather entity, which we create by calling

.. literalinclude:: code/scenario_1.py
   :start-at: weather =
   :end-before: # end

This will instruct the ``weathersim`` simulator to create one entity of the model *Function* (the model has the pretty generic name *Function* here because we are using the generic input simulator instead of a specialized weather simulator).
When creating a *Function* entity, we need to specify a Python function which will be used to generate its outputs.
This function will get the time as an input, though we just ignore this value here and return a random value between 0 and 1000 each time.
(These values will serve as direct normal irradiance in W/m² later.)
Data that we pass to a simulator while creating an entity of one of its models is called a *parameter* or short *param* of that model or entity.
So in this case, *function* is a param of the *Function* model.

Each simulator and model will expect different data as its params.
The simulator's documentation should describe which params are necessary or supported.

Next, we will create 50 entities of the *PV* model in our PV simulator, so that we can simulate 50 PV systems in the grid.
We could create these entities by calling ``pvsim.PV(...)`` 50 times in a loop, but there is a shorter way:

.. literalinclude:: code/scenario_1.py
   :start-at: pvs =
   :end-before: # end

By using the ``create`` method, we ask the simulator to create several instances at once.
The first parameter to ``create`` the number of copies that we want to create.
All further arguments are params of the model.
In this case, we specify the area of our PV systems (in :math:`\textrm{m}^2`), the latitude where the system is placed, its efficiency and the angles describing how it is tilted in space (in degrees).
When using ``create`` to create several entities, all of them will have the same values for their params.
If you want each entity to have different params, you will need to write a loop, after all.
However, ``create`` is often a useful shortcut because each of the created entities can still have unique connections.

Now, we create the grid by calling:

.. literalinclude:: code/scenario_1.py
   :start-at: grid =
   :end-before: # end

Which creates a *Grid* entity using the function ``create_cigre_network_lv`` from the ``pandapower.networks`` module that is part of pandapower.

Here, we get to see another feature of entities: they may have children, which are additional entities created automatically when their parent entity is created.
In the case of ``grid``, the children are all the grid elements like buses, lines, loads, transformers, and so on, that make up the grid topology that we specified when creating the grid entity.

.. admonition:: Why child entities?

   In the case of a grid topology, a detailed description of the grid usually already exists in some format directly readable by our grid simulator of choice.
   If we wanted to create entities corresponding to all the elements in the grid in our scenario script, we would probably end up parsing that format only to pass the data to a piece of software that would have been much better equipped to parse the format itself.
   This would be unnecessarily cumbersome, so we ask the simulator to do the parsing itself by referencing the file (or similar) describing the grid.

   However, we still want access to all the different elements in the grid so that we can connect other entities of our co-simulation to them specifically.
   For this reason, mosaik allows simulators to return additional entities to the ones that were requested explicitly.
   These additional entities are called *children* of the requested entities.

So we have an entity ``grid`` that represents the grid in its entirety.
It has children, representing all the elements in that grid.
They can be accessed via ``grid.children`` and if you print this, you will get a long list of objects each looking like this:

.. code-block::

   Entity('Grid', 'Bus-0', 'Grid', Bus, [], <mosaik.simmanager.LocalProcess object at 0x7fc60bdd2b60>)

In order, each object’s fields are:

- The simulator ID (``'Grid'``)
- The entity ID (``'Bus-0'``)
- The simulator name, as given in your ``SIM_CONFIG`` (``'Grid'``)
- The model of the entity (``Bus``)
- A list of that entity’s own children (``[]``)
- The internal object representing the connection to the simulator

We can use these fields to filter the list for the entities that we want.
We want to connect our PV entities to buses, so we only want entities of type *Bus*.
We also want to connect our PV system to a low-voltage bus and not to any of the medium-voltage buses that represents the connection to the external grid.
Luckily, the pandapower adapter reports the nominal voltage of each bus as so-called *extra info*, which is stored in the ``extra_info`` field of the corresponding entity.
We can filter for the buses we want by looking for buses with a nominal voltage of :math:`0.4\,\mathrm{kV}` (i.e. :math:`400\,\mathrm{V}`), like so:

.. literalinclude:: code/scenario_1.py
   :start-after: # filter buses
   :end-before: # end

We also want to read off the real and reactive power values that result at the connection to the higher grid levels.
This connection is represented by the *ExternalGrid* entity which we get like this:

.. literalinclude:: code/scenario_1.py
   :start-at: ext_grid = 
   :end-before: # end

.. literalinclude:: code/scenario_1.py
   :start-at: output =
   :end-before: # end

Doing Charlotte's work
======================

The last step in setting up our simulation is to spin a web of connections between our entities.

First, each PV system needs access to the weather data:

.. literalinclude:: code/scenario_1.py
   :start-after: # connect weather to pv
   :end-before: # end

We loop over all elements of our ``pvs`` list.
For each ``pv`` we establish a connection from the ``weather`` entity to the ``pv`` entity.
To do this, we need to specify which attributes should be connected.
*Attributes* are (the names for) the values that are exchanged while the simulation is running (as opposed to params that are used during setup).
Here, we connect the *value* attribute of the ``weather`` entity to the *DNI* attribute of the ``pv`` entity.
The simulator’s documentation should list the attributes of its models, whether they are used for input or output, and in which format they expect or provide their data.

Next, we want to connect our PV systems to the grid.
In this example scenario, we don’t care about the precise buses, so we can use the function ``connect_randomly`` from ``mosaik.util``.
It takes two lists of entities and connects each entity from the first list to one of the entities from the second list, using the specified attributes.
It tries to avoid connecting several entities to the same target, if possible:

.. literalinclude:: code/scenario_1.py
   :start-after: # connect pv to buses
   :end-before: # end

The *p_mw* (real power in MW) attribute of each PV system is connected to the *P_gen[MW]* attribute of its randomly chosen bus.
The *gen* suffix in the attribute names of the pandapower adapter says that these attributes follow the generator convention (i.e. power generation is positive).
There are corresponding *load* attributes as well, that follow the consumer convention (i.e. consumption is positive).

Finally, we want to see how our PV systems influence the power levels at the external grid.
So we extract the *ExternalGrid* entity from the grid’s children and connect it to our output simulator:

.. literalinclude:: code/scenario_1.py
   :start-after: # connect ext_grid
   :end-before: # end

This looks very similar to the calls above, but note that the attribute names are not given as a pair.
(There are no parentheses around ``"P[MW]", "Q[MVar]"``.)
This is actually a combination of two shortcuts in mosaik's ``connect`` method:

1. In case that the names of the two attributes that you want to connect are identical, you can just give the name of the attribute as a string once (instead of a pair of two strings).
   mosaik will then use this name for both the output and input attribute.
2. The ``connect`` method is variadic in the number of attribute connections.
   By giving multiple attributes (or attribute pairs), connections are established between all of them.
   So in this case, the *P[MW]* output attribute of the ``ext_grid`` entity is connected to the *P[MW]* input attribute of the ``output`` entity, and likewise, the *Q[MVar]* output attribute is connected to the *Q[MVar]* input attribute.

These shortcuts make things slightly more convenient whenever attribute names happen to line up.
In the case of the output simulator, we can have it this way because it will accept input on any attribute and just store the input under that name in a dictionary.

Run, mosaik, run
================

We are almost set to run the scenario now.
However, we first need to obtain a reference to the output simulator's internal dictionary to access the data afterwards.
(mosaik closes the connection immediately at the end of the simulation, so it would be too late by then.)
For this, the output simulator provides the ``get_dict`` extra method, which requires that we give it the entity ID for which we want to receive the output:

.. literalinclude:: code/scenario_1.py
   :start-at: result =
   :end-before: # end

Having set up our simulation, we can now run it, using:

.. literalinclude:: code/scenario_1.py
   :start-at: world.run(
   :end-before: # end

Given our step-size convention above, this will run 4 actual simulation steps.
Finally, we can inspect the output via

.. literalinclude:: code/scenario_1.py
   :start-after: # start print
   :end-before: # end
