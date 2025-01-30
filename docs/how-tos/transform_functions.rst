========================================================
Converting units from one simulator to another in mosaik
========================================================

.. currentmodule:: mosaik.scenario

The **transform function** feature in mosaik allows users to modify data dynamically when transferring outputs from one simulator to another. 
This feature provides a mechanism for applying transformations, scaling, or other processing steps before data reaches its destination.

Typical use cases for transform functions in mosaik are:

- Scaling data points (i.e. applying unit conversions)
- Implementing simple computational logic for real-time adjustments

Defining a transform function
-----------------------------

A transform function must be a :class:`~collections.abc.Callable` (e.g. a function or lambda) that takes a single argument (the input value) and returns a modified value. 
It can be added to :meth:`~World.connect` and any of its derivatives (e.g. :func:`~mosaik.util.connect_many_to_one`, :meth:`~World.connect_one`) call as a keyword argument using the key 'transform'.

Example 1: Scaling a value
^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

    # Define a simple scaling function
    def scale_value(value: float) -> float:
        return value * 1.5  # Scale up by a factor of 1.5

    world.connect(entity_1, entity_2, 'value', transform=scale_value)


Example 2: Nullifying negative values
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

    # Define a function that ensures only non-negative values are passed
    def filter_negative(value: float) -> float:
        return max(value, 0)

    world.connect(entity_1, entity_2, 'value', transform=filter_negative)


Handling edge cases
-------------------

Transform functions are independent of the simulators they work with, which means that the user is responsible for handling edge cases they want to avoid when handling these simulators.
If the simulator that acts as the data source is prone to giving invalid values, take care of them in a way that suits your simulation.

.. code-block:: python

    def safe_transform(value: float | None) -> float:
        if value is None:
            return 0.0  # Provide a default value
        return value * 2

    world.connect(entity_1, entity_2, 'value', transform=safe_transform)

