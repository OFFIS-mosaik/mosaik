.. _low-level-api:

=================
The Low-Level API
=================

The low-level API uses standard TCP sockets. If mosaik starts a simulator, that
simulator needs to connect to mosaik. If mosaik connects to a running instance
of a simulator, that simulator obviously needs to provide a server socket that
mosaik can connect to.

Network messages consists of a four bytes long *header* and a *payload* of
arbitrary length. The header is an unsigned integer (`uint32
<http://pubs.opengroup.org/onlinepubs/9699919799/basedefs/stdint.h.html#tag_13_47_03_01>`_)
in network byte order (big-endian) and stores the number of bytes in the
payload. The payload itself is a UTF-8 encoded `JSON <http://www.json.org/>`_
list containing the message type, a message ID and the actual content:

.. image:: /_static/network-messages.*
   :width: 500
   :align: center
   :alt: Messages consist of a header and a payload. The payload is a JSON
         list containing a message type, ID and the actual content.

Messages send between mosaik and a simulator must follow the `request-reply
pattern <http://en.wikipedia.org/wiki/Request-response>`_. That means, that
every request that one party makes must be responded by the other party.
Request use the message type ``0``, replies uses ``1`` for success or ``2`` to
indicate a failure. The message ID is an integer that is unique for every
request that a network socket makes. Replies (no matter if successful or
failed) need to use the message ID of the corresponding request.

The content of a request roughly map to a Python function call:

.. code-block:: json

   [function, [arg0, arg1, ...], {kwarg0: val0, kwar1: val1}]

Thereby, *function* is always a string. The type of the `arguments and keyword
arguments <https://docs.python.org/3/glossary.html#term-argument>`_ may vary
depending on the function.

The content of replies is either the return value of the request, or an error
message or stack trace. Error messages and stack traces should always be
strings. The return value for successful requests depends on the function.


Example
=======

We want to perform the following function call on the remote site:
``my_func('hello', 'world', times=23) --> 'the return value'``. This would map
to the following message payload:

.. code-block:: json

   [0, 1, ["my_func", ["hello", "world"], {"times": 23}]]

Our message is a request (message type ``0``), the message ID is ``1`` and the
content is a JSON list containing the function name as well as its arguments
and keyword arguments.

The complete message sent via the network will be::

   \x00\x00\x00\x36[1, 1, ["my_func", ["hello", "world"], {"times": 23}]]

In case of success, the reply's payload to this request could look like this:

.. code-block:: json

   [1, 1, "the return value"]

In case of error, this could be the reply's payload:

.. code-block:: json

   [2, 1, "Error in your code line 23: ..."]

The actual network messages would be::

   \x00\x00\x00\x1a[1, 1, "the return value"]
   \x00\x00\x00\x29[2, 1, "Error in your code line 23: ..."]

All commands that mosaik may send to a simulator are described in-depth in the
:ref:`next section <api-calls>`. All asynchronous requests that a simulator may
make are described in :ref:`asynchronous-requests`.

API calls:

- :ref:`api.init`
- :ref:`api.create`
- :ref:`api.step`
- :ref:`api.get_data`
- :ref:`api.stop`

Async. requests:

- :ref:`rpc.get_progress`
- :ref:`rpc.get_related_entities`
- :ref:`rpc.get_data`
- :ref:`rpc.set_data`


.. _api-calls:

API calls
=========


.. _api.init:

init
----

::

   ["init", [], {**sim_params}] -> meta

The ``init`` call is made once to initialize the simulator. It has no
positional arguments and an arbitrary amount of keyword arguments
(*sim_params*).

The return value *meta* is an object with meta data about the simulator::

    {
        "api_version": "x.y.z",
        "models": {
            "ModelName": {
                "public": true|false,
                "params": ["param_1", ...],
                "attrs": ["attr_1", ...],
            },
            ...
        }
    }

The *api_version* is a string that defines which version of the mosaik API the
simulator implements. The simulator's `major versions <http://semver.org/>`_
("x", in the snippet above) has to be the same as mosaik's. Mosaik will cancel
the simulation if a version mismatch occurs.

*models* is an object describing the models provided by this simulator. The
entry *public* determines whether a model can be instantiated by a user
(``true``) or if it is a sub-model that cannot be created directly (``false``).
*params* is a list of parameter names that can be passed to the model when
creating it. *attrs* is a list of attribute names that can be accessed (reading
or writing).


Example
^^^^^^^

Request:

.. code-block:: json

    ["init", [], {"step_size": 60}]

Reply:

.. code-block:: json

    {
       "api_version": "2.0",
       "models": {
            "Grid": {
                "public": true,
                "params": ["topology_file"],
                "attrs": []
            },
            "Node": {
                "public": false,
                "params": [],
                "attrs": ["P", "Q"]
            },
            "Branch": {
                "public": false,
                "params": [],
                "attrs": ["I", "I_max"]
            }
        }
    }


.. _api.create:

create
------

::

   ["create", [num, model], {**model_params}] -> entity_list


Create *num* instances of *model* using the provided *model_params*

*num* is an integer for the number of model instances to create.

*model* needs to be a public entry in the simulator's ``meta['models']`` (see
:ref:`api.init`).

*model_params* is an object mapping parameters (from
``meta['models'][model]['params']``, see :ref:`api.init`) to their values.

Return a (nested) list of objects describing the created model instances
(entities). The root list must contain exactly *num* elements. The number of
objects in sub-lists is not constrained::

   [
         {
            "eid": "eid_1",
            "type": "model_name",
            "rel": ["eid_2", ...],
            "children": <entity_list>,
         },
         ...
   ]

The entity ID (*eid*) of an object must be unique within a simulator instance.
For entities in the root list, *type* must be the same as the *model*
parameter. The type for objects in sub-lists may be anything that can be found
in ``meta['models']`` (see :ref:`api.init`).  *rel* is a list of related
entities. The *children* entry is optional and may contain a sub-list of
entities.


Example
^^^^^^^

Request:

.. code-block:: json

    ["create", [1, "Grid"], {"topology_file": "data/grid.json"}]

Reply:

.. code-block:: json

    [
        {
            "eid": "Grid_1",
            "type": "Grid",
            "rel": [],
            "children": [
                {
                    "eid": "node_0",
                    "type": "Node",
                    "rel": []
                },
                {
                    "eid": "node_1",
                    "type": "Node",
                    "rel": []
                },
                {
                    "eid": "branch_0",
                    "type": "Branch",
                    "rel": ["node_0", "node_1"]
                }
            ]
        }
    ]


.. _api.step:

step
----

::

   [] -> null


Example
^^^^^^^

Request:

.. code-block:: json

    []

Reply:

.. code-block:: json

    null


.. _api.get_data:

get_data
--------

::

   [] -> null


Example
^^^^^^^

Request:

.. code-block:: json

    []

Reply:

.. code-block:: json

    null


.. _api.stop:

stop
----

::

   [] -> null


Example
^^^^^^^

Request:

.. code-block:: json

    []

Reply:

.. code-block:: json

    null


.. _asynchronous-requests:

Asynchronous requests
=====================

.. _rpc.get_progress:

get_progress
------------


.. _rpc.get_related_entities:

get_related_entities
--------------------


.. _rpc.get_data:

get_data
--------


.. _rpc.set_data:

set_data
--------


