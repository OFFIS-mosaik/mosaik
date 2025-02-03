========================================================
Converting units from one simulator to another in mosaik
========================================================

.. currentmodule:: mosaik.scenario

Sometimes, you want to connect two simulators via mosaik but their inputs and outputs do not quite line up.
Maybe they use different units, or a different convention for whether power generation should have a positive or negative sign.
Sometimes, the right solution to these problems is to add another simulator to your simulator to perform the necessary adaptation.
But in case of very simply transformations, this is quite cumbersome.
For these situations, mosaik provides the ability to add **transform functions** to your connections.

Typical use cases for transform functions in mosaik are:

- Scaling data points (i.e. applying unit conversions)
- Implementing *simple* computational logic for real-time adjustments

Defining a transform function
-----------------------------

A transform function must be a :class:`~collections.abc.Callable` (e.g. a function or lambda) that takes a single argument (the input value) and returns a modified value.
It can be added to :meth:`~World.connect` and any of its derivatives (e.g. :func:`~mosaik.util.connect_many_to_one`, :meth:`~World.connect_one`) call as a keyword argument using the key 'transform'.

Example 1: Transforming units
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Say we are connecting two simulators which both work with power values.
However, one of them expresses them in watts, while the other uses mega-watts.
Here transform functions come to rescue, without requiring changing one of the involved simulators or adding additional "converter simulators" to our simulation:

.. code-block:: python

    def transform_W_to_MW(value: float) -> float:
        return value * 1e-6

    world.connect(entity_1, entity_2, "P", transform=transform_W_to_MW)


Example 2: Nullifying negative values
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In this example, we have a simulator that for some reason has separate attributes for consumption and generation, and only accepts non-negative values on both.
However, we want to provide inputs from a battery which can provide both consumption and generation and uses the sign to express this.

.. code-block:: python

    def only_positive_part(value: float) -> float:
        return max(value, 0)

    def only_negative_part(value: float) -> float
        return -min(value, 0)  # the negative part is the positive version of the value if it was negative

    world.connect(battery, load, "P", transform=only_positive_part)
    world.connect(battery, gen, "P", transform=only_negative_part)


Handling edge cases
-------------------

Sometimes, simulators have idiosyncratic output for edge cases.
For example, a simulator might return ``None`` to indicate that no power was produced, where the destination simulator would prefer to receive ``0.0`` instead.
This can also be solved with transform functions:

.. code-block:: python

    def safe_transform(value: float | None) -> float:
        if value is None:
            return 0.0  # Provide a default value
        return value

    world.connect(entity_1, entity_2, 'value', transform=safe_transform)

In cases like this, you should make sure, however, that your transformation is actually semantically valid.
If the source simulator actually uses ``None`` to represent a problem (and not as a strange way of saying "no power was produced"), you might be hiding actual bugs in your simulation when you replace these values by ``0.0``.
