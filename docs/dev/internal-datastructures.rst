Measurements and Events
=======================

In mosaik 4, entities are no longer identified by entity IDs.
Instead, they are referred to by their numerical index within their model.
This entity index is called *eidx* for short.

For example, if a simulator has two models *Bus* and *Line*, there could be *Bus* entities with indices 0, 1, 2, 3, and *Line* entities with indices 0, 1, 2.

Since mosaik 4, we also have a strong distinction between measurements (representing physical values that are always present) and events (representing messages etc., which only exist at certain moments in time, and where potentially, multiple values might exist at the same time).

These two types of value use different code paths to respect their corresponding properties.

**Measurements** are stored in Arrow record batches, with one record batch per model.
Each entity of that model then gets a row in the record batch, and each attribute gets a column; thus exactly one value per attribute is stored for each entity.

Each simulator's :class:`SimRunner` will store the latest output in this format.
Other simulator's :class:`SimRunner` objects will then query that stored data, which can be done efficiently using Arrow's compute functions, working on the level of attributes/columns:
First, using a precomputed :attr:`take_mask`, the source simulator's outputs are selected and reordered; including potenitally duplicating values if needed (when one entity's output is sent to multiple receivers).
This gives a column of the right length per source.
Then, a :attr:`choice_mask` is used to determine which simulator's output is actually used for each entity's input (multiple different simulators might provide inputs to different entities on the same attribute).

The datatypes organizing this are :class:`MeasurementAssembly`, :class:`MeasurementSource` and its subclasses :class:`SimulatorSource` (for data actually coming from other simulators) and :class:`ConstantSource` (for when the scenario author sets an entity's input to a constant value).

**Events** are also stored in record batches per model, but the structure is completely differnt:
There are always exactly three columns *time*, *eidx*, and *value*.
*time* contains tuples of integers specifying the event's time.
*eidx* is the numerical index of the entity receiving the event.
*value* is the actual value, stored as an Arrow union with one variant per attribute.
This way, the different event attributes can be used independently.
It is legal for the same entity to receive multiple value for the same attribute at the same time; the receiving simulator should handle this case (raising an exception, if necessary).

Unlike measurements, event data is immediately transmitted to (and then stored in) the receiving simulator's :class:`SimRunner`.
When stepping, it will filter its list of all future events for the ones relevant for the current step.
