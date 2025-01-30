=======================
Simulator API Reference
=======================

This is the reference for mosaik's simulator API, meaning the ways to connect new tools and programming languages to mosaik.
If you are implementing a scenario using existing simulators, the :doc:`scenario API reference </api_reference/index>` is relevant, instead.


The low- and high-level mosaik API
==================================

Communication between mosaik and the connected simulators can happen in two different ways:

First, there is a protocol based on TCP connections and JSON datastructures.
We call this the **low-level mosaik API**.
For some programming languages (including Python, Java, and Julia), there are wrappers around this low-level API that abstract away the need to deal with JSON and TCP connections.
We call these wrappers **high-level mosaik APIs**.

Second, in the case of Python specifically, mosaik can also use simulators implementing the high-level API directly, skipping JSON and TCP entirely.

The high-level API for Python is what is used in the tutorial and the Python-specific how-to guides.
The reference for its classes and methods can be found here.

For the high-level APIs in other programming languages, see their respective documentation.

(TODO: add links)

The figure below depicts the differences between the two API levels.

.. image:: /_static/mosaik-api.*
    :width: 500
    :align: center
    :alt: Mosaik's low- and high-level API


In this section, we document both the high-level API for Python, and the low-level API.
*You generally do not need the documentation of the low-level API unless you are implementing a simulator in a programming language that has no high-level API or you are implementing a high-level API yourself.

.. toctree::
   :maxdepth: 1
   :caption: Contents

   overview
   low-level
   high-level
   high-level-other-languages
