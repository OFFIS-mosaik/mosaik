================================================================
``mosaik.in_or_out_set`` -- Classes for attribute specifications
================================================================

.. currentmodule:: mosaik.in_or_out_set

.. automodule:: mosaik.in_or_out_set
   :members:
   :exclude-members: InOrOutSet

   .. py:type:: InOrOutSet[E]
      :canonical: OutSet | frozenset

      (The type parameter ``E`` is actually passed on to ``OutSet`` and ``frozenset``, which we cannot properly document due to limitations in Sphinx.)

      An InOrOutSet is either a FrozenSet or an OutSet.
      This means that it can represent either
      - a finite number of elements of the type E or
      - all but a finite number of element of the type E.

      Standard set-theoretic operations (union, intersection, etc.) can still be computed for InOrOutSets and will result in a InOrOutSet again.
