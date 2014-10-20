.. _high-level-api:

==================
The high-level API
==================

Currently, there is only a high-level API for Python. Once there are
implementations for other languages available, this document will be updated.


Installation
============

The Python implementation of the mosaik API is available as a separate package
an can easily be installed via `pip <https://pip.pypa.io>`_:

.. code-block:: bash

   pip install mosaik-api

It supports Python 2.7, >= 3.3 and PyPy.


Usage
=====

You create a subclass of :class:`mosaik_api.Simulator` which implements the
four API calls :meth:`~mosaik_api.Simulator.init()`,
:meth:`~mosaik_api.Simulator.create()`, :meth:`~mosaik_api.Simulator.step()`
and :meth:`~mosaik_api.Simulator.get_data()`. You can optionally override
:meth:`~mosaik_api.Simulator.configure()` and
:meth:`~mosaik_api.Simulator.finalize()`. The former allows you to handle
additional command line arguments that your simulator may need. The latter is
called just before the simulator terminates and allows you to perform some
clean-up.

You then call :func:`mosaik_api.start_simulation()` from your `main()` function
to get everything set-up and running. That function handles the networking as
well as serialization and de-serialization of messages. Commands from the
low-level API are translated to simple function calls. The return value of
these functions is used for the reply.

For example, the message

.. code-block:: json

    ["create", [2, "Model", {"param1": 15, "param2": "spam"}]

will result in a call

.. code-block:: python

    create(2, 'Model', param1=15, param2='spam')

API calls
---------

.. module:: mosaik_api
.. autoclass:: Simulator
   :members: init, create, step, get_data, configure, finalize

   .. autoattribute:: meta
      :annotation:

   .. autoattribute:: mosaik
      :annotation:

The *mosaik-api* package provides an `example simulator
<https://bitbucket.org/mosaik/mosaik-api-python/src/tip/example_sim/mosaik.py>`_
that demonstrates how the API can be implemented.


Asynchronous requests
---------------------

The :ref:`asynchronous requests <asynchronous-requests>` can be called via the
``MosaikRemote`` proxy ``self.mosaik`` from within
:meth:`~mosaik_api.Simulator.step()`. They don't return the actual results but
an *event* (similar to a *future* of *deferred*). The event will eventually
hold the actual result. To wait for that result to arrive, you simply yield
the event, e.g.:

.. code-block:: python

    def step(self, time, inputs):
        progress = yield self.mosaik.get_progress()
        # ...

.. currentmodule:: mosaik.simmanager

.. automethod:: MosaikRemote.get_progress
   :noindex:

.. automethod:: MosaikRemote.get_related_entities
   :noindex:

.. automethod:: MosaikRemote.get_data
   :noindex:

.. automethod:: MosaikRemote.set_data
   :noindex:

The *mosaik-api* package provides an `example “multi-agent system”
<https://bitbucket.org/mosaik/mosaik-api-python/src/tip/example_mas/mosaik.py>`_
that demonstrates how to perform asynchronous requests can be implemented.


Starting the simulator
----------------------

To start your simulator, you just need to create an instance of your
:class:`~mosaik_api.Simulator` sub-class and pass it to
:func:`~mosaik_api.start_simulation()`:

.. currentmodule:: mosaik_api
.. autofunction:: start_simulation

Here is an example with a bit more context:

.. code-block:: python

    import mosaik_api


    example_meta = {
        'models' {
            'A': {
                  'public': True,
                  'params': ['init_val'],
                  'attrs': ['val_out', 'dummy_out'],
            },
        }
    }


    class ExampleSim(mosaik_api.Simulator):
        def __init__(self):
            super().__init__(example_meta)

        sim_name = 'ExampleSimulation'

        def configure(self, args, backend, env):
            # Here you could handle additional command line arguments

        def init(self, sid):
            # Initialize the simulator
            return self.meta

        # Implement the remaining methods (create, step, get_data, ...)


    def main():
        import sys

        description = 'A simple example simulation for mosaik.'
        extra_options = [
           '--foo       Enable foo',
           '--bar BAR   The bar parameter',
        ]

        return mosaik_api.start_simulation(ExampleSim(), description, extra_options)


    if __name__ == '__main__':
        sys.exit(main())
