============
Installation
============

mosaik is a Python library, so you need a working installation of Python to use it.
You might already have one, but if you don't, you will need to install Python.
Python's official website is https://python.org.
They also have a beginner's guide with `installation instructions for different operating systems here <https://wiki.python.org/moin/BeginnersGuide/Download>`__.

mosaik itself is then published on the Python Package Index *PyPI* `here <https://pypi.org/project/mosaik/>`__.
If you have a preferred way of installing Python packages, we recommend that you keep using that.
(Python's built-in tool ``pip``; ``uv`` (`here <https://github.com/astral-sh/uv>`__); packaging tools integrated into your text editor or IDE; Anaconda; etc.)

If you are entirely new to this, we recommend that you start with virtual environments.
They help to separate Python packages used for different projects which greatly reduces the number of versioning conflicts that you will encounter.

.. admonition:: Short intro to using virtual environments

   When setting up a Python project for the first time, in the folder containing it, you call ``python -m venv .venv``.
   This will create the folder *.venv* which will hold the Python interpreter and packages used for this project.

   Whenever you want to work on this project (including right after creating it), you call ``.venv\Scripts\activate`` (on Windows) or ``. .venv/bin/activate`` (on Unix, including MacOS; note the ``.`` at the start).
   This will activate the virtual environment, which should be reflected by the commandline prompt now starting with ``(.venv)``.

   Python tools (like ``python`` itself, but also ``pip``) will now work in this virtual environment, cleanly separating it from other Python projects you might have.

   When you are done working on the project, you can call ``deactivate`` to use your global Python environment again.
   Alternatively, closing the terminal will also do that; in any new terminal you open, you will have to activate the virtual environment again.

   Many editors also integrate virtual environments and will allow you to select which one to use somewhere in their interface.
   Often, they're even detected automatically if you use a common name like *.venv* for them.

For more, see `Python's official documentation for virtual environments here <https://docs.python.org/3/tutorial/venv.html>`__.


The mosaik demo
===============

We have a (somewhat out-dated) demo scenario that you can try here: https://gitlab.com/mosaik/examples/mosaik-demo.
Download and unpack it (or better yet, clone it with Git).
Then, create a virtual environment in the *mosaik-demo* folder and activate it, as explained above.
With the virtual environment active, install the demo's requirements by calling::

   pip install -e .

Then, you can run the scenario with ``python demo.py``.
Open a webbrowser to http://localhost:8000 to see the running simulation.


Getting help
============

Sometimes things go wrong, but we are usually quite willing to help.
The best place to ask questions is our `GitHub discussions forum`_, where we and other people might be able to answer your questions.

.. _GitHub discussions forum: https://github.com/orgs/OFFIS-mosaik/discussions

If you think that you have found a bug in mosaik, or if you want to propose a new feature, you can do that using our `issue tracker on GitLab`_.
(Yes, mosaik is present on both GitHub and GitLab for historic reasons.)
Note that our team is small and often bound by other project work, so we cannot promise that we will follow up on every feature request.
However, we are genuinely interested in constantly improving mosaik, and every feedback helps.

.. _issue tracker on GitLab: https://gitlab.com/mosaik/mosaik/-/issues

Finally, if your question is not suited for a public forum, you can also reach us via e-mail at mosaik@offis.de.


Working with the source
=======================

If you want to play around with mosaik's source code yourself, you can find it on GitLab `here <https://gitlab.com/mosaik/mosaik>`_, where you can also clone the repository.
Note that we do not recommend installing mosaik this way if you just want to use it.
Installing the package from PyPI will make it much easier to update to a new version.
