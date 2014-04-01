============
Installation
============

This guide contains detailed installation instructions for :ref:`linux`,
:ref:`os-x` and :ref:`windows`.


.. _linux:

Linux
=====

This guide is based on *(K)ubuntu 14.04 Trusty Tahr, 64bit (beta 2)*.

Mosaik and the demo scenario require `Python`__ >= 3.3. Ubuntu ships with
Python 3.4, so everything is okay.

1. We also need `pip`__, a package manager for Python packages, and
   `virtualenv`__, which can create isolated Python environments for different
   projects:

   .. code-block:: bash

      $ wget https://raw.github.com/pypa/pip/master/contrib/get-pip.py
      $ sudo python get-pip.py
      $ sudo pip install virtualenv

   Optionally, you can also install `virtualenvwrapper`__ which makes working with
   *virtualenv* easier. It's not necessary if you just want to get the demo
   running, but very useful if you keep developing with Python.

2. Now we need to create a virtual environment for mosaik and its dependencies.
   The common location for venvs is under :file:`~/.virtualenvs/`:

   .. code-block:: bash

      $ virtualenv -p /usr/bin/python3 ~/.virtualenvs/mosaik
      $ source ~/.virtualenvs/mosaik/bin/activate

   Your command line prompt should now start with "(mosaik)" and roughly look
   like this: ``(mosaik)user@kubuntu:~$``.

3. The final step is to install mosaik:

   .. code-block:: bash

       (mosaik)$ pip install --pre mosaik

   Mosaik should no be installed successfully.

__ https://www.python.org/
__ https://pip.readthedocs.org/
__ https://virtualenv.readthedocs.org/
__ https://virtualenvwrapper.readthedocs.org/


Running the demo
----------------

Mosaik alone is not very useful, so we also provide a small demo scenario and
some simple simulators as well as a mosaik binding for `PYPOWER`__.

1. PYPOWER requires *NumPy* and *SciPy*. You can *a)* use the packages shipped
   with Ubuntu (faster, easier, but they may be outdated, recommended if you
   just want to run the demo scenario) or *b)* compile them on your own (a bit
   more complicated, takes longer, recommended for development). In both cases,
   you also need to install *Mercurial* and *Git*:

   a. We use :program:`apt-get` to install NumPy and SciPy (as well as
      Mercurial and Git). By default, venvs are isolated from globally
      installed packages. To make them visible, we also have to recreate the
      venv and set the ``--system-site-packages`` flag:

      .. code-block:: bash

         $ sudo apt-get install mercurial git python3-numpy python3-scipy
         $ rm -rf ~/.virtualenvs/mosaik
         $ virtualenv -p /usr/bin/python3 --system-site-packages ~/.virtualenvs/mosaik
         $ source ~/.virtualenvs/mosaik/bin/activate

   b. In order to compile NumPy and SciPy, we need to install some build
      dependencies (and Mercurial and Git). We then build binary `wheel`__
      packages that we can later reuse without re-compiling everything. We'll
      store these *wheels* in :file:`~/wheelhouse/`:

      .. code-block:: bash

         $ sudo apt-get instal mercurial git build-essential python3-dev gfortran libatlas-dev libatlas-base-devl
         $ source ~/.virtualenvs/mosaik/bin/activate
         (mosaik)$ pip install wheel
         (mosaik)$ pip wheel numpy
         (mosaik)$ pip install wheelhouse/numpy-1.8.1-cp34-cp34m-linux_x86_64.whl
         (mosaik)$ pip wheel scipy
         (mosaik)$ pip install wheelhouse/scipy-0.13.3-cp34-cp34m-linux_x86_64.whl

2. You can now clone the `mosaik-demo repoistory`__ into a folder where you
   store all your code and repositories (we'll use :file:`~/Code/`):

   .. code-block:: bash

      (mosaik)$ mkdir ~/Code
      (mosaik)$ hg clone https://bitbucket.org/mosaik/mosaik-demo ~/Code/mosaik-demo

3. Now we only need to install all requirements (mosaik and the simulators) and
   can finally run the demo:

   .. code-block:: bash

      (mosaik)$ ~/Code/mosaik-demo/
      (mosaik)$ pip install -r requirements.txt
      (mosaik)$ python demo.py

   If no errors occur, you can now open the `web visualization`__. You can
   click the nodes of the topology graph to show a timeline of their values.
   You can also drag them around to rearrange them.

   You can cancel the simulation by pressing :kbd:`Ctrl-C`.

__ https://github.com/rwl/PYPOWER
__ https://wheel.readthedocs.org/
__ https://bitbucket.org/mosaik/mosaik-demo
__ http://localhost:8000


.. _os-x:

OS X
====


.. _windows:

Windows
=======


