==============
The mosaik API
==============

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
<https://bitbucket.org/mosaik/mosaik-api-python>`_ and `Java
<https://bitbucket.org/mosaik/mosaik-api-java>`_. Implementations for other
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
