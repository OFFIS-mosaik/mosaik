.. _upgrading_from_mosaik2:

============================
Upgrading from mosaik 2 to 3
============================

Mosaik 3 has some new features which required some API changes. For the time
being simulators implementing mosaik-api 3 are still supported, but you will
get a deprecation warning at the beginning. In case that you don't want to use
any of the new features you could :ref:`stay with mosaik 2 <sticking_with_v2>`.
But otherwise the upgrade to mosaik 3 is quite easy, as you will see in the
following sections:


Component's type
================

Simulation components now have a *type* (*time-based*, *event-based*, or
*hybrid*) to indicate which simulation time paradigm they implement. See
details :ref:`here <stepping_types>`. The type is set in the component's meta
data, which the component returns to mosaik via the API's
:ref:`init <api.init>` function.


Time resolution
===============

A global :ref:`time resolution <time_resolution>` is now defined for each
scenario indicating how to translate mosaik's integer time to simulated time.
It can be set at the instantiation of the simulation's :class:`World` in the
:ref:`setup of the scenario <scenario_definition>` and is set to *1.* by
default. It's value is passed to the components via the :ref:`init <api.init>`
function.


Max_advance time
================
*max_advance* tells the simulator how far it can advance its time without
risking any causality error, i.e. it is guaranteed that no external step will
be triggered before max_advance + 1. It is determined for each step and passed
to the component as third positional argument of the API's :ref:`init <api.step>`
function.

.. _sticking_with_v2:

Sticking with mosaik 2
======================

In case that you don't want to upgrade to mosaik 3, the mosaik dependency must
be pinned to version 2.x.

When installing mosaik with ``pip``, you get the latest mosaik 2.x version via:

.. code-block:: shell

   pip install 'mosaik<3'

You can also specify this constraint in a `requirements files
<https://pip.pypa.io/en/stable/user_guide/#requirements-files>`_:

.. code-block:: text

   mosaik<3

Or in the ``install_requires`` list in a ``setup.py`` file:

.. code-block:: python

   setup(
       ...
       install_requires=['mosaik<3'],
       ...
   )
