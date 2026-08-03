=======================
Simulator API Reference
=======================

This is the reference for mosaik's simulator API, meaning the ways to connect new tools and programming languages to mosaik.
If you are implementing a scenario using existing simulators, the :doc:`scenario API reference </api_reference/index>` is relevant, instead.
For a list of simulators already connected to mosaik, see :doc:`/ecosystem/index`.


The low- and high-level simulator API
=====================================

Communication between mosaik and the connected simulators can happen in two different ways:

First, there is a protocol based on TCP connections and JSON datastructures.
We call this the :doc:`low-level simulator API <low-level>`.

Second, for some programming languages (including Python, Java, and Julia), there are wrappers around this low-level API that abstract away the need to deal with JSON and TCP connections.
We call these wrappers **high-level simulator APIs** (see here for :doc:`Python <high-level>`, :doc:`other languages <high-level-other-languages>`).
You will usually want to use these when available.
The figure below depicts the differences between the two API levels.

.. image:: /_static/mosaik-api.*
    :width: 500
    :align: center
    :alt: mosaik's low- and high-level API

Second, in the case of Python specifically, mosaik can also use simulators implementing the high-level API directly, skipping JSON and TCP entirely.

In any of these cases, mosaik will call certain **mosaik methods** on your simulator.
The order and meaning of these is explained in :doc:`overview`.

.. toctree::
   overview
   high-level-other-languages
   high-level
   low-level
