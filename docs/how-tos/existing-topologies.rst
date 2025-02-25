=================================================
How to use existing topologies via child entities
=================================================

In most cases, a mosaik simulator should allow its users to create as many entities of its models as needed.
However, if the simulator's entities usually have elaborate internal connections (such as for grid simulators, for example), this can become cumbersome.
In these cases, it is often better to have the simulator create the entities based on some "topology" file in a suitable format.
(For example, a grid simulator's native grid file format.)
To integrate such simulators, mosaik offers the concept of **child entities**.
Here, we will explain the use of child entities both from the point of view of a scenario author and of a simulator author.


As a scenario author
====================

A simulator using child entities will usually say so in its documentation.
First, you start the simulator as normal::

    grid_sim = world.start("Grid")

Then, you need to get the entities.
As mosaik offers no way of returning entities outside of :meth:`~mosaik.scenario.ModelMock.create` (or its constructor form), you will need to create one entity yourself.
The name of the model for this should be documented with your simulator, and it is often also the only model marked as *public* in the simulator's :class:`~mosaik_api_v3.types.Meta` (which you can access as ``grid_sim.meta``, in the example).
For example::

    grid = grid_sim.Grid(grid_file="path/to/the/grid")

Depending on the simulator, this might be a singleton (meaning only one of these entities can be created) or not (which would allow running several grids in the same simulator).

A simulator following this style will then return all the entities you are actually interested in in its ``children`` field (like ``grid.children``).
This is a list of entities.
To get specific entities, there are a couple of options, depending on the simulator and your needs. In the following, ``entity`` is one element of the list of children.

- The simulator might have well-defined entity IDs, so you can find entities by filtering for ``entity.eid``.
- You might be interested in all entities of a specific type, like all buses in the grid.
  In this case, you can filter by ``entity.type``.
  This field will contain a model name of the simulator, so it determines which attributes the entity has.
- In some cases, just the entity type is not enough.
  For cases like this, a simulator can return additional information with each entity, which will be made available as the ``extra_info`` field on the ``entity``.
  (For example, while all buses in the grid are *Bus* entities, you might only be interested in a certain voltage level.
  For this use case, ``entity.extra_info["nominal voltage [kV]"]`` exists in the pandapower
  adapter, and you can filter for low-voltage nodes by only using those where this value is 0.4, which corresponds to 400V.)

One you have determined the right entities in the ``children`` list, you cann connect them like mosaik entities you have created yourself.

In very rare cases, child entities can also have children of their own, which allows for tree structures.
In this case, you could filter for entities recursively.


As a simulator author
=====================

As a simulator author, you should consider using child entities if creating all the individual entities that your simulator provides in the scenario script would be too cumbersome.
Also read the previous section to get an idea of what scenario authors reasonably expect from your simulator.

Creating a simulator with child entities usually starts with your :class:`~mosaik_api_v3.types.Meta`.
There, you define one type of entity representing the entirety of your topology (like *Grid* for a grid simulator) and then a number of additional types of entities for all the different components in your simulator that users might want to access individually (like *Bus*, *Line*, *Generator*, *Transformer*, *ExternalGrid*, etc. for a grid simulator).
Essentially, for each type of "thing" which exists in different numbers across different simulations, you should have a model.

.. note::
   Note that the models do not necessarily correspond to physical things; you could have a model representing an account for tracking income, or even a path through your topology, if this is an interesting object for a simulation.
   As much as possible, avoid creating variable numbers of attributes for things like this.
   Attributes need to be defined in the :class:`~mosaik_api_v3.types.Meta`, so you force your user to know everything when starting your simulator.
   If you represent things that vary in number by entities instead, they can be specified by the user later.

The models for these "things" will usually have their *public* field set to ``False``, unless it is sensible for users to also create additional ones themselves.
(In our experience, it is often useful to create a separate model for user-created instances, though.
So the grid simulator might have a *Gen* model and an *ExtraGen* model.)

In your :meth:`~mosaik_api_v3.Simulator.create` method, you will accept a specification of the topology to create (a file path, a standard name, etc.).
You read in the topology and create your internal representation of each entity.
When it comes to returning entities, you must return precisely the entity representing the entirety; however, for this entity you specify children.
For a grid simulator, this might look like::

    return [{
        "eid": "Grid",
        "type": "Grid",
        "children": [
            {
                "eid": "Bus-0",
                "type": "Bus",
                "rel": ["Line-0"],
                "extra_info": <see below>,
            },
            {
                "eid": "Line-0",
                "type": "Line"
                "rel": ["Bus-0", "Bus-1"],
                "extra_info": <see below>,
            },
            ...
        ],
    }]

The *type* of each of your children must appear in your :class:`~mosaik_api_v3.types.Meta`; this will tell mosaik which attributes these entities have.

There are two extra fields:

- *rel* allows you specify relations between your entities.
  These are not used by mosaik, but simulators can access the graph for their needs.
  (Usually, this is just used for visualizations.)
  The graph created by the relations is undirected; you don't need to specify both directions, but it also doesn't hurt.
- *extra_info* can contain whatever you want (as long as it can be serialized to JSON).
  You should provide information that will help scenario authors sift through the entity list.
  (For example, for buses in the grid, the nominal voltage helps; if the entities have IDs or names in the file format, these are are also frequently helpful.)

(Technically these also exist on non-child entities but they're less useful in that case.)

Some additional considerations
------------------------------

- Your parent entity can be a singleton (meaning, you raise an exception when the user tries to create more than one).
  This might make the implementation of your simulator more straight-forward.
  However, before you do this, you should consider how likely it is that users want to load multiple topologies in the same scenario.
- Sometimes it is a good idea to provide extra methods to disable entities.
  (For example, a grid might come with pre-created loads which the user might want to disable to then add their own.)
