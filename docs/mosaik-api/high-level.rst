.. _high-level-api:

==================
The High-Level API
==================

Currently, a high-level mosaik API is only available for *Python* and *Java*.
The remainder of this section fill focus on the Python implementation. However,
APIs for other Languages will expose the same functionality in
a similar way.

The high-level API automatically creates the required socket, connects to the
PM and starts a simple event loop that sends and receives messages and
(de)serializes their contents. Each command *cmd* is mapped to a method with
the same name and the contents of the parameters object *params* (which will be
a plain dict after the deserialization) are passed as keyword arguments (named
parameters).

For example, the message

.. code-block:: json

    ["init", {
        "step_size": 15,
        "sim_params": {"start":"2012-12-21"},
        "model_conf": []
    }]

will result in a call

.. code-block:: python

    init(step_size=15, sim_params={'start': '2012-12-21'}, model_conf=[])

The return value of that function is directly used for the *retval* placeholder
in the simulator’s reply to the PM. Note, that JSON's *object* type directly
maps to Python's *dictionary* (:class:`dict`) and JSON's *list* type maps to
Python's :class:`list`.

You only need to implement an interface with the according methods that makes
the appropriate calls to your simulator. The API therefore offers
a :class:`~mosaik_api.Simulator` base class,
that you simply can inherit from. This class also offers
a :meth:`~mosaik_api.Simulator.configure()` method that allows you to handle
additional command line arguments that your simulator may need. There is also
a :meth:`~mosaik_api.Simulator.finalize()` method; it is called just before
the simulator terminates and allows you to perform some clean-up like shutting
down sub-processes.

.. currentmodule:: mosaik_api
.. autoclass:: Simulator
    :members:

Asynchronous callbacks:

.. currentmodule:: mosaik.simmanager
.. automethod:: MosaikRemote.get_progress
.. automethod:: MosaikRemote.get_related_entities
.. automethod:: MosaikRemote.get_data
.. automethod:: MosaikRemote.set_data

There is also a method that you can call from your ``main()`` to start the
event loop:

.. currentmodule:: mosaik_api
.. autofunction:: start_simulation

The following listing shows how the API can be used:

.. code-block:: python

    from mosaik_api import Simulation, start_simulation


    class ExampleSim(Simulation):
        sim_name = 'ExampleSimulation'

        def configure(self, args):
            # Here you could handle additional commandline arguments

        def init(self, step_size, sim_params, model_conf):
            # Initialize the simulator and create all entities
            # and return the entity IDs

        # Implement the remaining methods (step, get_data, ...)


    if __name__ == '__main__':
        import sys

        description = 'A simple example simulation for mosaik.'
        extra_options = [
            (('-e', '--example'), {
                'help': 'This is just an example parameter',
                'default': True,
            }),
        ]

        sys.exit(start_simulation(ExampleSim(), description, extra_options))
