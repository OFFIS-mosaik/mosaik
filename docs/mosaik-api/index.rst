=======================
Simulator API Reference
=======================

This is the reference for mosaik's simulator API, meaning the ways to connect new tools and programming languages to mosaik.
If you are implementing a scenario using existing simulators, the scenario API reference is relevant, instead.


The low- and high-level mosaik API
==================================

Communication between mosaik and the connected simulators can happen in two different ways:

First, there is a protocol based on TCP connections and JSON datastructures.
We call this the *low-level mosaik API*.
For some programming languages (including Python, Java, and Julia), there are wrappers around this low-level API that abstract away the need to deal with JSON and TCP connections.
We call these wrappers *high-level mosaik APIs*.

Second, in the case of Python specifically, mosaik can also use simulators implementing the high-level API directly, skipping JSON and TCP entirely.

The high-level API for Python is what is used in the tutorial and the Python-specific how-to guides.
The reference for its classes and methods can be found here.

For the high-level APIs in other programming languages, see their respective documentation.

(TODO: add links)

In the following, we will explain the low-level API.
*You usually do not need to read this unless you are implementing a high-level API for a new programming language or you are writing a simulator in a programming language where no high-level API exists.*





The mosaik API defines the communication protocol between mosaik and the
simulators it couples. We differentiate between a *low-level* and
a *high-level* version of the API.

The low-level API uses plain `network sockets
<http://en.wikipedia.org/wiki/Network_socket>`_ to exchange `JSON
<http://www.json.org/>`_ encoded messages.

The high-level API is an implementation of the low-level API in a specific
programming language. It encapsulates all parts related to networking (socket
handling, an event loop, message (de)serialization) and provides an abstract
base class with a few methods that have to be implemented in a subclass.
A high-level API implementation is currently available for `Python
<https://gitlab.com/mosaik/mosaik-api-python>`_, `Java
<https://gitlab.com/mosaik/mosaik-api-java>`_ and `Julia <https://mosaik.gitlab.io/api/mosaik-api-julia>`_. Implementations for other
languages will be added when needed.

The figure below depicts the differences between the two API levels.

.. image:: /_static/mosaik-api.*
    :width: 500
    :align: center
    :alt: Mosaik's low- and high-level API

Contents:

.. toctree::
   :maxdepth: 1

   overview
   low-level
   high-level
   high-level-other-languages
