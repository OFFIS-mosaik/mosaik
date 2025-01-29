.. _transform_functions:

=============================
Converting units from one simulator to another in mosaik
=============================

Overview
--------

The **transform function** feature in mosaik allows users to modify data dynamically when transferring outputs from one simulator to another. This feature provides a mechanism for applying transformations, scaling, filtering, or other processing steps before data reaches its destination.

Transform functions are user-defined `Callable` objects that take an input value (typically a `float`) and return a processed value.

Use Cases
---------

- Filtering out invalid or noisy values
- Scaling data points (i.e. applying unit conversions)
- Implementing simple computational logic for real-time adjustments

Defining a transform function
-----------------------------

A transform function must be a `Callable` (e.g., a function or lambda) that takes a single argument (the input value) and returns a modified value.

Example 1: Scaling a value
^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

    # Define a simple scaling function
    def scale_value(value: float) -> float:
        return value * 1.5  # Scale up by a factor of 1.5

Example 2: Filtering negative values
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

    # Define a function that ensures only non-negative values are passed
    def filter_negative(value: float) -> float:
        return max(value, 0)


Handling edge cases
-------------------

Since transform functions are user-defined, consider the following best practices:

Ensure type consistency
^^^^^^^^^^^^^^^^^^^^^^^

Transform functions should return a valid numerical value. If there is a possibility of invalid inputs, handle them properly:

.. code-block:: python

    def safe_transform(value: float | None) -> float:
        if value is None:
            return 0.0  # Provide a default value
        return value * 2

Avoid exceptions
^^^^^^^^^^^^^^^^

Unhandled exceptions in the transform function can disrupt the simulation. Always catch potential errors:

.. code-block:: python

    def robust_transform(value: float) -> float:
        try:
            return value ** 2  # Square the value
        except TypeError:
            return 0.0  # Default fallback

Test with different inputs
^^^^^^^^^^^^^^^^^^^^^^^^^^

Ensure your function behaves as expected for all possible values, including edge cases:

.. code-block:: python

    assert scale_value(10) == 15.0
    assert filter_negative(-5) == 0
    assert safe_transform(None) == 0.0
    assert robust_transform("invalid") == 0.0

Summary
-------

- **Transform functions** enable dynamic data modification in mosaik.
- Functions must be `Callable`, accept a single value and handle edge cases gracefully.
- Properly designed transform functions enhance simulation flexibility and robustness.

By integrating transform functions, you can fine-tune data exchange in mosaik to better suit your modeling needs.