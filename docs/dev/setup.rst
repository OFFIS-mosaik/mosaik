===========================
Development setup and tests
===========================

This guide will show you how to set up a development environment for mosaik
or components of its ecosystem (like the `Python API
<https://bitbucket.org/mosaik/mosaik-api-python>`_), how to run the tests,
check the code coverage and quality, and build the documentation.


General advice
==============

- You should use Linux or OS X as your main development platform – most tools
  are working much better there than on Windows. However, you should still make
  sure that mosaik keeps working on Windows. ;-)

- You should create a separate virtualenv for each project, that you are going
  to work on (e.g., one for *mosaik*, another one for *mosaik-api-python*
  and so forth). This will make it easier for you to track their dependencies.

- You should install and use `virtualenvwrapper
  <http://virtualenvwrapper.readthedocs.org/en/latest/>`_. It will make working
  with multiple virtualenvs much easier.

- You may need to change some absolute paths from the code blocks depending on
  you system.

- I'll only explain the necessary steps for *mosaik*, because its the most
  complex project (e.g., *mosaik-api-python* has no separate documentation).

- You should have worked through the general :doc:`installation instructions
  <../installation>` and got the demo running. Afterwards delete the virtualenv
  *mosaik* (:command:`rmvirtualenv mosaik`) – you can later recreate it as
  *moaik-demo*.


Installation
============

Change to the directory where you keep your code and clone the
mosaik-repository. Create a virtualenv with a Python 3 interpreter and install
all development dependencies. Finally, install mosaik in `editable mode
<https://pip.pypa.io/en/latest/reference/pip_install.html?highlight=editable#editable-installs>`_:

.. code-block:: bash

   $ cd ~/Code
   $ hg clone ssh://hg@bitbucket.org/mosaik/mosaik
   $ cd mosaik
   $ mkvirtualenv -p /usr/bin/python3 mosaik
   (mosaik)$ pip install -r requirements.txt
   (mosaik)$ pip install -e .  # Install mosaik in "editable"

An "editable" installation just means, that changes you introduce in the
repository are automatically reflected in you installation (and thus in your
tests).


Tests and coverage
==================

To run all tests, simply execute :command:`py.test`:

.. code-block:: bash

   $ py.test

It will automatically run all code examples in the :file:`docs/` as well as the
actual tests from :file:`mosaik/test/`. Pytest's behavior can be controlled via
the ``[pytest]`` section in the `setup.cfg` file and via command line arguments
(see its `documentation <http://pytest.org/latest/>`_ or :command:`py.test
--help`).

You should also regularly check the code/branch coverage:

.. code-block:: bash

   $ py.test --cov=mosaik

You can also generate HTML files from your source that highlight uncovered
lines:

.. code-block:: bash

   $ py.test --cov=mosaik --cov-report=html
   $ [kde-]open htmlcov/index.html

Take a look at the `docs of pytest-cov
<https://github.com/schlamar/pytest-cov>`_ for more help.

Before making a release (and in between) you should make sure that the tests
are passing on all supported Python versions. You do this with `tox
<http://tox.readthedocs.org/en/latest/>`_. Tox' config file :file:`tox.ini`
will show you which versions we support. Every interpreter listed here (e.g.,
Python 3.3 or PyPy) should be installed on your system. Running tox is than
very easy:

.. code-block:: bash

   $ tox
   ...
   _______ summary ________
   py33: commands succeeded
   py34: commands succeeded
   congratulations :)



Coding style
============

Mosaik follows -- as most Python projects -- relatively strict coding
standards.

- All source files are encoded with *UTF-8*

- *LF* (``\n``) is used to represent a new line (Unix style).

- Four spaces are used for indentation (three spaces for reStructuredText
  directives).

- Trailing whitespaces should always be stripped.

- Lines should be no longer than 79 characters.

- Python files should be formatted according to `PEP
  8 <http://legacy.python.org/dev/peps/pep-0008/>`_ and `PEP 257
  <http://legacy.python.org/dev/peps/pep-0257/>`_.

You should regularly run `flake8 <https://flake8.readthedocs.org/en/latest/>`_
to perform PEP8 style checks and and run some analyses to find things like
unused imports:

.. code-block:: bash

   $ flake8 mosaik

It takes its configuration from :file:`setup.cfg`.


Build the documentation
=======================

We use `Sphinx <http://sphinx-doc.org/>`_ to create mosaik's documentation:

.. code-block:: bash

   $ cd docs/
   $ make html

This will build the documentation to :file:`docs/_build/html`.

When you push new revisions to mosaik's main repo
(``bitbucket.org/mosaik/mosaik``) the `official documentation
<https://mosaik.readthedocs.org>`_ is automatically updated via a hook.
