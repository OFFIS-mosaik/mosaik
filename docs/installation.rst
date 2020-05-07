============
Installation
============

This guide contains detailed installation instructions for :ref:`linux`,
:ref:`os-x` and :ref:`windows`.

It covers the installation of the mosaik framework followed by the instructions
to install the demo.


.. _linux:

Linux
=====

This guide is based on *(K)ubuntu 18.04 Bionic Beaver, 64bit*.

Mosaik and the demo scenario require `Python`__ >= 3.6, which should be fine
for any recent linux distribution. Note that we test mosaik only for the most
(typically three) recent python versions though.

1. We also need `pip`__, a package manager for Python packages, and
   `virtualenv`__, which can create isolated Python environments for different
   projects:

   .. code-block:: bash

      $ wget https://bootstrap.pypa.io/get-pip.py
      $ sudo python get-pip.py
      $ sudo pip install -U virtualenv

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


Running the demo
----------------

Mosaik alone is not very useful (because it needs other simulators to perform
a simulation), so we also provide a small demo scenario and some simple
simulators as well as a mosaik binding for `PYPOWER`__.

1. PYPOWER requires *NumPy* and *SciPy*. We also need to install the revision
   control tool *git*. You can use the packages shipped
   with Ubuntu. We use :program:`apt-get` to install NumPy, SciPy, and h5py as 
   well as git. By default, venvs are isolated from globally installed
   packages. To make them visible, we also have to recreate the venv and set
   the ``--system-site-packages`` flag:

   .. code-block:: bash

      $ sudo apt-get install git python3-numpy python3-scipy python3-h5py
      $ rm -rf ~/.virtualenvs/mosaik
      $ virtualenv -p /usr/bin/python3 --system-site-packages ~/.virtualenvs/mosaik
      $ source ~/.virtualenvs/mosaik/bin/activate


2. You can now clone the `mosaik-demo repository`__ into a folder where you
   store all your code and repositories (we'll use :file:`~/Code/`):

   .. code-block:: bash

      (mosaik)$ mkdir ~/Code
      (mosaik)$ git clone https://gitlab.com/mosaik/mosaik-demo.git ~/Code/mosaik-demo

3. Now we only need to install all requirements (mosaik and the simulators) and
   can finally run the demo:

   .. code-block:: bash

      (mosaik)$ cd ~/Code/mosaik-demo/
      (mosaik)$ pip install -r requirements.txt
      (mosaik)$ python demo.py

   If no errors occur, the last command will start the demo. The web visualisation
   shows the demo in your browser: http://localhost:8000. You can click the nodes of the 
   topology graph to show a time series of their values. You can also drag them 
   around to rearrange them.
   
   You can cancel the simulation by pressing :kbd:`Ctrl-C`.

__ https://github.com/rwl/PYPOWER
__ https://gitlab.com/mosaik/mosaik-demo


.. _os-x:

OS X
====

This guide is based on *OS X 10.11 El Capitan*.

1. Mosaik and the demo scenario require `Python`__ >= 3.6. OS X only ships with
   some outdated versions of Python, so we need to install a recent Python 2
   and 3 first. The `recommended way`__ of doing this is with the packet manager `homebrew`__.
   To install homebrew, we need to open a *Terminal* and execute the following command:

   .. code-block:: bash

      $ ruby -e "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)"

   The homebrew installer asks you to install the *command line developer
   tools* for "xcode-select". Install them. When you are done, go back to the
   terminal and press :kbd:`Enter` so that the installer continues.

   If this doesn't work for you, you'll find more detailed instructions in the
   `homebrew wiki`__.

   Once the installation is successful, we can install ``python`` and
   ``python3``:

   .. code-block:: bash

      $ brew install python python3

   This will also install the Python package manager `pip`__.

2. Next, we need `virtualenv`__ which can create isolated Python
   environments for different projects:

   .. code-block:: bash

      $ pip install -U virtualenv


3. Now we need to create a virtual environment for mosaik and its dependencies.
   The common location for venvs is under :file:`~/.virtualenvs/`:

   .. code-block:: bash

      $ virtualenv -p /usr/local/bin/python3 ~/.virtualenvs/mosaik
      $ source ~/.virtualenvs/mosaik/bin/activate

   Your command line prompt should now start with "(mosaik)" and roughly look
   like this: ``(mosaik)user@macbook:~$``.

4. The final step is to install mosaik:

   .. code-block:: bash

       (mosaik)$ pip install mosaik

   Mosaik should now be installed successfully.

__ https://www.python.org/
__ http://docs.python-guide.org/en/latest/starting/install/osx/
__ http://brew.sh/
__ https://github.com/Homebrew/homebrew/wiki/Installation
__ https://pip.readthedocs.org/
__ https://virtualenv.readthedocs.org/


Running the demo
----------------

Mosaik alone is not very useful (because it needs other simulators to perform
a simulation), so we also provide a small demo scenario and some simple
simulators as well as a mosaik binding for `PYPOWER`__.

1. To clone the demo repository, we need to install *git*. In order to
   compile *NumPy*, *SciPy* and *h5py* (which are required by PYPOWER and the
   database adapter) we also need to install *gfortran* which is included in *gcc*. You should deactivate
   the venv for this:

   .. code-block:: bash

      (mosaik)$ deactivate
      $ brew install git gcc hdf5
      $ source ~/.virtualenvs/mosaik/bin/activate

2. For NumPy and SciPy we build binary `wheel`__ packages that we can later
   reuse without re-compiling everything. We'll store these *wheels* in
   :file:`~/wheelhouse/`:

   .. code-block:: bash

      (mosaik)$ pip install wheel
      (mosaik)$ pip wheel numpy
      (mosaik)$ pip install wheelhouse/numpy-1.10.1-cp35-cp35m-macosx_10_6_intel.macosx_10_9_intel.macosx_10_9_x86_64.macosx_10_10_intel.macosx_10_10_x86_64.whl
      (mosaik)$ pip wheel scipy
      (mosaik)$ pip install wheelhouse/scipy-0.16.0-cp35-cp35m-macosx_10_6_intel.macosx_10_9_intel.macosx_10_9_x86_64.macosx_10_10_intel.macosx_10_10_x86_64.whl
      (mosaik)$ pip wheel h5py
      (mosaik)$ pip install wheelhouse/h5py-2.5.0-cp35-cp35m-macosx_10_6_intel.macosx_10_9_intel.macosx_10_9_x86_64.macosx_10_10_intel.macosx_10_10_x86_64.whl
      
.. note::
    The file names of the *wheels* (\*.whl-files) may change when version-numbers 
    change. Please check the output of *pip install* or the directory :file:`~/wheelhouse/`
    for the exact file names.
      
2. You can now clone the `mosaik-demo repository`__ into a folder where you
   store all your code and repositories (we'll use :file:`~/Code/`):

   .. code-block:: bash

      (mosaik)$ mkdir ~/Code
      (mosaik)$ git clone https://gitlab.com/mosaik/mosaik-demo.git ~/Code/mosaik-demo

3. Now we only need to install all requirements (mosaik and the simulators) and
   can finally run the demo:

   .. code-block:: bash

      (mosaik)$ cd ~/Code/mosaik-demo/
      (mosaik)$ pip install -r requirements.txt
      (mosaik)$ python demo.py

   If no errors occur, the last command will start the demo. The web visualisation
   shows the demo in your browser: http://localhost:8000. You can click the nodes of the 
   topology graph to show a time series of their values. You can also drag them 
   around to rearrange them.

   You can cancel the simulation by pressing :kbd:`Ctrl-C`.

__ https://github.com/rwl/PYPOWER
__ https://wheel.readthedocs.org/
__ https://gitlab.com/mosaik/mosaik-demo


.. _windows:

Windows
=======

This guide is based on *Windows 10, 64bit*.

1. Mosaik and the demo scenario require `Python`__ >= 3.6. By default, it will
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

   This also install the Python package manager `pip`__.

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
      terminal with administarator privileges (right-click the Terminal icon,
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

       (mosaik) C:\Users\yourname> pip install mosaik

   Mosaik should now be installed successfully.

__ https://mosaik.offis.de/install/#windows-installer
__ https://www.python.org/
__ https://www.python.org/downloads/release/python-382/
__ https://pip.readthedocs.org/
__ https://virtualenv.readthedocs.org/


Running the demo
----------------

Mosaik alone is not very useful (because it needs other simulators to perform
a simulation), so we also provide a small demo scenario and some simple
simulators as well as a mosaik binding for `PYPOWER`__.

1. Download and install `git`__.

   **Restart the command** prompt (as Admin if necessary and make sure you are
   in the right directory again) and activate the virtualenv again:

   .. code-block:: bat

      C:\Users\yourname> Envs\mosaik\Scripts\activate.bat

2. Clone the demo repository:

   .. code-block:: bat

      (mosaik)C:\Users\yourname> git clone https://gitlab.com/mosaik/mosaik-demo.git

3. Now we only need to install all requirements (mosaik and the simulators) and
   can finally run the demo:

   .. code-block:: bat

      (mosaik)C:\Users\yourname> cd mosaik-demo
      (mosaik)C:\Users\yourname\mosaik-demo> pip install -r requirements.txt
      (mosaik)C:\Users\yourname\mosaik-demo> python demo.py

   The web visualisation shows the demo in your browser: http://localhost:8000. 
   You can click the nodes of the topology graph to show a timeline of their values.
   You can also drag them around to rearrange them.

   You can cancel the simulation by pressing :kbd:`Ctrl-C`. More exceptions
   may be raised. No problem. :-)

__ https://github.com/rwl/PYPOWER
__ https://git-scm.com/downloads
