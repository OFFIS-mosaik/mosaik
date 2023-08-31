.. _high-level-api:

==================
The high-level API
==================

Currently, there are high-level APIs for Python, Java, C#, and MatLab.


Installation
============

The Python implementation of the mosaik API is available as a separate package
an can easily be installed via `pip <https://pip.pypa.io>`_:

.. code-block:: bash

   pip install mosaik-api-v3

It supports Python 2.7, >= 3.3 and PyPy.

Java-API
========
For the use of the Java-API please refer to the :doc:`Java-tutorial</tutorials/tutorial_api-java>`.

.. note:: There is also an extended version for java at :doc:`Java-tutorial</tutorials/tutorial_api-java-generics>` that incorporates QoL changes for a more java-like experience.


Usage
=====

You create a subclass of :class:`mosaik_api_v3.Simulator` which implements the
four API calls :meth:`~mosaik_api_v3.Simulator.init()`,
:meth:`~mosaik_api_v3.Simulator.create()`, :meth:`~mosaik_api_v3.Simulator.step()`
and :meth:`~mosaik_api_v3.Simulator.get_data()`. You can optionally override
:meth:`~mosaik_api_v3.Simulator.configure()` and
:meth:`~mosaik_api_v3.Simulator.finalize()`. The former allows you to handle
additional command line arguments that your simulator may need. The latter is
called just before the simulator terminates and allows you to perform some
clean-up.

You then call :func:`mosaik_api_v3.start_simulation()` from your `main()` function
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

.. module:: mosaik_api_v3
.. autoclass:: Simulator
   :members: init, create, setup_done, step, get_data, configure, finalize

   .. _meta:
   .. autoattribute:: meta
      :annotation:

   .. autoattribute:: mosaik
      :annotation:

   .. autoattribute:: time_resolution
      :annotation:

The *mosaik-api-v3* package provides an `example simulator
<https://gitlab.com/mosaik/mosaik-api-python/-/blob/master/example_sim/mosaik.py>`_
that demonstrates how the API can be implemented.


Asynchronous requests
---------------------

The :ref:`asynchronous requests <asynchronous-requests>` can be called via the
``MosaikRemote`` proxy ``self.mosaik`` from within
:meth:`~mosaik_api_v3.Simulator.step()`, except for ``set_data()`` which has to
be called from another thread/process (see below). They don't return the
actual results but an *event* (similar to a *future* of *deferred*). The event
will eventually hold the actual result. To wait for that result to arrive, you
simply yield the event, e.g.:

.. code-block:: python

    def step(self, time, inputs, max_advance):
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

.. automethod:: MosaikRemote.set_event
   :noindex:

The *mosaik-api-v3* package provides an `example "multi-agent system"
<https://gitlab.com/mosaik/mosaik-api-python/-/blob/master/example_mas/mosaik.py>`_
that demonstrates how asynchronous requests can be implemented.


Starting the simulator
----------------------

To start your simulator, you just need to create an instance of your
:class:`~mosaik_api_v3.Simulator` sub-class and pass it to
:func:`~mosaik_api_v3.start_simulation()`:

.. currentmodule:: mosaik_api_v3
.. autofunction:: start_simulation

Here is an example with a bit more context:

.. code-block:: python

    import mosaik_api_v3


    example_meta = {
        'type': 'time-based',
        'models' {
            'A': {
                  'public': True,
                  'params': ['init_val'],
                  'attrs': ['val_out', 'dummy_out'],
            },
        }
    }


    class ExampleSim(mosaik_api_v3.Simulator):
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

        return mosaik_api_v3.start_simulation(ExampleSim(), description, extra_options)


    if __name__ == '__main__':
        sys.exit(main())
