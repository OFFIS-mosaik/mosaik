============
Installation
============

This guide contains detailed installation instructions for :ref:`linux`,
:ref:`os-x` and :ref:`windows`.


.. _linux:

Linux
=====

This guide is based on *(K)ubuntu 14.04 Trusty Tahr, 64bit*.

Mosaik and the demo scenario require `Python`__ >= 3.3. Ubuntu ships with
Python 3.4, so everything is okay.

1. We also need `pip`__, a package manager for Python packages, and
   `virtualenv`__, which can create isolated Python environments for different
   projects:

   .. code-block:: bash

      $ wget https://bootstrap.pypa.io/get-pip.py
      $ sudo python get-pip.py
      $ sudo pip install -U virtualenv

   Optionally, you can also install `virtualenvwrapper`__ which makes working
   with *virtualenv* easier. It's not necessary if you just want to get the
   demo running, but very useful if you keep developing with Python.

2. Now we need to create a virtual environment for mosaik and its dependencies.
   The common location for venvs is under :file:`~/.virtualenvs/`:

   .. code-block:: bash

      $ virtualenv -p /usr/bin/python3 ~/.virtualenvs/mosaik
      $ source ~/.virtualenvs/mosaik/bin/activate

   Your command line prompt should now start with "(mosaik)" and roughly look
   like this: ``(mosaik)user@kubuntu:~$``.

3. The final step is to install mosaik:

   .. code-block:: bash

       (mosaik)$ pip install mosaik

   Mosaik should now be installed successfully.

__ https://www.python.org/
__ https://pip.readthedocs.org/
__ https://virtualenv.readthedocs.org/
__ https://virtualenvwrapper.readthedocs.org/


Running the demo
----------------

Mosaik alone is not very useful (because it needs other simulators to perform
a simulation), so we also provide a small demo scenario and some simple
simulators as well as a mosaik binding for `PYPOWER`__.

1. PYPOWER requires *NumPy* and *SciPy*. You can *a)* use the packages shipped
   with Ubuntu (faster, easier, but they may be outdated, recommended if you
   just want to run the demo scenario) or *b)* compile them on your own (a bit
   more complicated, takes longer, recommended for development). In both cases,
   you also need to install *Mercurial*:

   a. We use :program:`apt-get` to install NumPy, SciPy, and h5py (as well as
      Mercurial). By default, venvs are isolated from globally installed
      packages. To make them visible, we also have to recreate the venv and set
      the ``--system-site-packages`` flag:

      .. code-block:: bash

         $ sudo apt-get install mercurial python3-numpy python3-scipy python3-h5py
         $ rm -rf ~/.virtualenvs/mosaik
         $ virtualenv -p /usr/bin/python3 --system-site-packages ~/.virtualenvs/mosaik
         $ source ~/.virtualenvs/mosaik/bin/activate

   b. In order to compile NumPy and SciPy, we need to install some build
      dependencies (and Mercurial). We then build binary `wheel`__ packages
      that we can later reuse without re-compiling everything. We'll store
      these *wheels* in :file:`~/wheelhouse/`:

      .. code-block:: bash

         $ sudo apt-get install mercurial build-essential python3-dev gfortran libatlas-dev libatlas-base-dev libhdf5-dev
         $ source ~/.virtualenvs/mosaik/bin/activate
         (mosaik)$ pip install wheel
         (mosaik)$ pip wheel numpy
         (mosaik)$ pip install wheelhouse/numpy-1.8.2-cp34-cp34m-linux_x86_64.whl
         (mosaik)$ pip wheel scipy
         (mosaik)$ pip install wheelhouse/scipy-0.14.0-cp34-cp34m-linux_x86_64.whl
         (mosaik)$ pip wheel h5py
         (mosaik)$ pip install wheelhouse/h5py-2.3.1-cp34-cp34m-linux_x86_64.whl

2. You can now clone the `mosaik-demo repository`__ into a folder where you
   store all your code and repositories (we'll use :file:`~/Code/`):

   .. code-block:: bash

      (mosaik)$ mkdir ~/Code
      (mosaik)$ hg clone https://bitbucket.org/mosaik/mosaik-demo ~/Code/mosaik-demo

3. Now we only need to install all requirements (mosaik and the simulators) and
   can finally run the demo:

   .. code-block:: bash

      (mosaik)$ cd ~/Code/mosaik-demo/
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

This guide is based on *OS X 10.9 Mavericks*.

1. Mosaik and the demo scenario require `Python`__ >= 3.3. OS X only ships with
   some outdated versions of Python, so we need to install a recent Python 2
   and 3 first. The `recommended way`__ of doing this is with `homebrew`__.
   Therefore, we need to open *Terminal* and execute the following command:

   .. code-block:: bash

      $ ruby -e "$(curl -fsSL https://raw.github.com/Homebrew/homebrew/go/install)"

   The homebrew installer may ask you to install the *command line developer
   tools* for "xcode-select". Install them. When you are done, go back to the
   terminal and press :kbd:`Enter` so that the installer continues.

   If this doesn't work for you, you'll find more detailed instructions in the
   `homebrew wiki`__.

   Once the installation is successful, we can install ``python`` and
   ``python3``:

   .. code-block:: bash

      $ brew install python python3

   This will also install the Python package manager `pip`__.

2. Furthermore, we need `virtualenv`__ which can create isolated Python
   environments for different projects:

   .. code-block:: bash

      $ pip install -U virtualenv

   Optionally, you can also install `virtualenvwrapper`__ which makes working
   with *virtualenv* easier. It's not necessary if you just want to get the
   demo running, but very useful if you keep developing with Python.

3. Now we need to create a virtual environment for mosaik and its dependencies.
   The common location for venvs is under :file:`~/.virtualenvs/`:

   .. code-block:: bash

      $ virtualenv -p /usr/local/bin/python3 ~/.virtualenvs/mosaik
      $ source ~/.virtualenvs/mosaik/bin/activate

   Your command line prompt should now start with "(mosaik)" and roughly look
   like this: ``(mosaik)user@macbook:~$``.

4. The final step is to install mosaik:

   .. code-block:: bash

       (mosaik)$ pip install --pre mosaik

   Mosaik should now be installed successfully.

__ https://www.python.org/
__ http://docs.python-guide.org/en/latest/starting/install/osx/
__ http://brew.sh/
__ https://github.com/Homebrew/homebrew/wiki/Installation
__ https://pip.readthedocs.org/
__ https://virtualenv.readthedocs.org/
__ https://virtualenvwrapper.readthedocs.org/


Running the demo
----------------

Mosaik alone is not very useful (because it needs other simulators to perform
a simulation), so we also provide a small demo scenario and some simple
simulators as well as a mosaik binding for `PYPOWER`__.

1. To clone the demo repository, we need to install *Mercurial*. In order to
   compile *NumPy*, *SciPy* and *h5py* (which are required by PYPOWER and the
   database adapter) we also need to install *gfortran*. You should deactivate
   the venv for this:

   .. code-block:: bash

      (mosaik)$ deactivate
      $ brew install hg gfortran hdf5

2. For NumPy and SciPy we build binary `wheel`__ packages that we can later
   reuse without re-compiling everything. We'll store these *wheels* in
   :file:`~/wheelhouse/`:

   .. code-block:: bash

      $ source ~/.virtualenvs/mosaik/bin/activate
      (mosaik)$ pip install wheel
      (mosaik)$ pip wheel numpy
      (mosaik)$ pip install wheelhouse/numpy-1.8.2-cp34-cp34m-macosx_10_9_x86_64.whl
      (mosaik)$ pip wheel scipy
      (mosaik)$ pip install wheelhouse/scipy-0.14.0-cp34-cp34m-macosx_10_9_x86_64.whl
      (mosaik)$ pip wheel h5py
      (mosaik)$ pip install wheelhouse/h5py-2.3.1-cp34-cp34m-macosx_10_9_x86_64.whl

2. You can now clone the `mosaik-demo repository`__ into a folder where you
   store all your code and repositories (we'll use :file:`~/Code/`):

   .. code-block:: bash

      (mosaik)$ mkdir ~/Code
      (mosaik)$ hg clone https://bitbucket.org/mosaik/mosaik-demo ~/Code/mosaik-demo

3. Now we only need to install all requirements (mosaik and the simulators) and
   can finally run the demo:

   .. code-block:: bash

      (mosaik)$ cd ~/Code/mosaik-demo/
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


.. _windows:

Windows
=======

.. note::

   There is currently no one-click-exe-installer for mosaik. This is due to
   its early development stage. The installion process will get easier in the
   future, though.

This guide is based on *Windows 7, 64bit*.

1. Mosaik and the demo scenario require `Python`__ >= 3.3. By default, it will
   offer you a 32bit installer. You can find the *Windows x86-64 MSI installer*
   `here`__.

   1. When the download finished, double-click the installer.

   2. Select *Install for all users* and click *Next >*.

   3. The default installation path is okay. Click *Next >*.

   4. In the *Customize Python* page, click on the *Python* node and select
      *Entire feature will be installed on local hard drive*. Make sure that
      *Add python.exe to Path* is enabled. Click *Next >*.

   5. When Windows asks you to allow the installation, allow the installation.
      Wait. Click *Finish*.

   This also installed Python package manager `pip`__.

2. We also need `virtualenv`__ which can create isolated Python environments
   for different projects.

   Open a terminal window: Press the :kbd:`Windows` key (or click on the start
   menu) and enter ``cmd``. Press :kbd:`Enter`. Your terminal prompt should
   look like ``C:\Users\yourname>``. Execute the following command to install
   virtualenv:

   .. code-block:: bat

      C:\Users\yourname> pip install -U virtualenv

   .. note::

      If your Windows account type is *Standard User*, you need to open the
      terminal with administarator priviledges (right-click the Terminal icon,
      then *open as Administrator*). Make then sure that you are in your user
      directory:

      .. code-block:: bat

         C:\Windows\system32> cd \Users\yourname
         C:\Users\yourname>

3. Now we need to create a virtual environment for mosaik and its dependencies.
   The common location for venvs is under :file:`Envs/` in your users
   directory:

   .. code-block:: bat

      C:\Users\yourname> virtualenv -p C:\Python34\python.exe Envs\mosaik
      C:\Users\yourname> Envs\mosaik\Scripts\activate.bat

   Your command line prompt should now start with "(mosaik)" and roughly look
   like this: ``(mosaik) C:\Users\yourname>``.

4. The final step is to install mosaik:

   .. code-block:: bat

       (mosaik) C:\Users\yourname> pip install --pre mosaik

   Mosaik should now be installed successfully.

__ https://www.python.org/
__ https://www.python.org/downloads/release/python-342/
__ https://pip.readthedocs.org/
__ https://virtualenv.readthedocs.org/


Running the demo
----------------

Mosaik alone is not very useful (because it needs other simulators to perform
a simulation), so we also provide a small demo scenario and some simple
simulators as well as a mosaik binding for `PYPOWER`__.

1. PYPOWER requires *NumPy* and *SciPy* and the database adapter requires
   *h5py*. Christoph Gohlke `provides`__ installers for them (`NumPy`__,
   `SciPy`__, `h5py`__). Select the appropriate files for your Python
   installation (32bit or 64bit, Python version), e.g.,
   *numpy‑MKL‑1.8.2.win‑amd64‑py3.4.exe*,
   *scipy‑0.14.0.win‑amd64‑py3.4.exe*, *h5py-2.3.1.win-amd64-py3.4.exe*.

   .. note::

      Run ``python -c "import sys; print(sys.version)"`` from the command promt
      in order to get the system architecture and Python version.

      If you have a 64bit Windows, but installed a 32bit Python, also use
      the 32bit versions of NumPy etc.

   Download them into your downloads folder and install them via the following
   commands:

   .. code-block:: bat

      (mosaik) C:\Users\yourname> easy_install Downloads\numpy-MKL-1.9.0.win-amd64-py3.4.exe
      (mosaik) C:\Users\yourname> easy_install Downloads\scipy-0.14.0.win-amd64-py3.4.exe
      (mosaik) C:\Users\yourname> easy_install Downloads\h5py-2.3.1.win-amd64-py3.4.exe

2. Download and install `Mercurial`__.

   **Restart the command** prompt (as Admin if necessary and make sure you are
   in the right directory again) and activate the virtualenv again:

   .. code-block:: bat

      C:\Users\yourname> Envs\mosaik\Scripts\activate.bat

2. Clone the demo repository:

   .. code-block:: bat

      (mosaik)C:\Users\yourname> hg clone https://bitbucket.org/mosaik/mosaik-demo

3. Now we only need to install all requirements (mosaik and the simulators) and
   can finally run the demo:

   .. code-block:: bat

      (mosaik)C:\Users\yourname> cd mosaik-demo
      (mosaik)C:\Users\yourname\mosaik-demo> pip install -r requirements.txt
      (mosaik)C:\Users\yourname\mosaik-demo> python demo.py

   An exception may be raised at the end of the installation, but as long as
   before that exception there was the output *Successfully installed PYPOWER
   mosaik-csv mosaik-householdsim ...*, everything is okay.

   You can now open the `web visualization`__. You can
   click the nodes of the topology graph to show a timeline of their values.
   You can also drag them around to rearrange them.

   You can cancel the simulation by pressing :kbd:`Ctrl-C`. More exceptions
   may be raised. No problem. :-)

__ https://github.com/rwl/PYPOWER
__ http://www.lfd.uci.edu/~gohlke/pythonlibs/
__ http://www.lfd.uci.edu/~gohlke/pythonlibs/#numpy
__ http://www.lfd.uci.edu/~gohlke/pythonlibs/#scipy
__ http://www.lfd.uci.edu/~gohlke/pythonlibs/#h5py
__ http://mercurial.selenic.com/
__ http://localhost:8000
