========================================
How to use mosaik with Jupyter notebooks
========================================

Getting mosaik and Jupyter to work together requires an extra step.
This is because both mosaik and Jupyter want to create and control an :class:`asyncio.EventLoop`, but these event loops cannot be nested by default.

To resolve this, there are two solutions:

1. You can use the library `nest-asyncio <https://pypi.org/project/nest-asyncio/>`_. Install it and call

   .. code-block:: python

      import nest_asyncio
      nest_asyncio.apply()

   at the beginning of your scenario notebook (before creating the mosaik ``World``).

2. Alternatively, you can switch to using an :class:`~mosaik.async_scenario.AsyncWorld`.
   This version of :class:`~mosaik.scenario.World` does not control the event loop itself.
   In exchange, you need to call some of the mosaik methods as coroutines (i.e. using ``await``).
   See :ref:`async-mosaik` for more on this.

There is a second problem that can occur if you also implement your own simulators:
Namely, a Jupyter notebook cannot be imported using Python's import mechanism by default.
As mosaik uses the import mechanism to start simulators, writing a *simulator* in a notebook file does not work out of the box.
To resolve this, either write your simulators in Python files, or import the `import-ipynb <https://pypi.org/project/import-ipynb/>`_ library in your *scenario* (not simulator) notebook.

Jupyter example
===============

Despite these challenges, we have an example repository demonstrating the use of mosaik in a Jupyter notebook `here <https://gitlab.com/mosaik/examples/mosaik-tutorials-on-binder>`_.
You can either start it on Binder, or you can clone the repository and run the example in a local Jupyter instance.
