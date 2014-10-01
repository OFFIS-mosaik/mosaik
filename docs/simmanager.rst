=====================
The simulator manager
=====================

The simulator manager (or just *sim manager*) is responsible for starting and
handling the external simulator processes involved in a simulation as well as
for the communication with them.

Usually, these simulators will be started as separate sub-processes which will
then connect to mosaik via network sockets. This has two benefits:

1. Simulators can be written in any language.

2. Simulation steps can be performed in parallel, if two processes don't depend
   on each others data.

Simulators written in Python 3 can, for performance reasons, be imported and
executed like normal Python modules. This way, all Sim API calls will be plain
functions calls without the overhead of network communication and message
(de)serialization. However, since Python only runs in one thread at a time,
this will also prevent parallel execution of simulators.

When a (Python 3) simulator is computationally inexpensive, running it
in-process may give you good results. If it performs a lot of expensive
computations, it may be better to start separate processes which can then do
these computations in parallel. In practice, you should try and profile both
ways in order to get the maximum performance out of it.

Sometimes, both ways won't work because you simply cannot start the simulator
process by yourself. This might be the reason for hardware-in-the-loop or if
a simulator needs to run on a separate machine. In these cases, you can simply
let mosaik connect to a running instance of such a simulator.

Internally, all three kinds of simulator processes (in-process with mosaik,
started by mosaik, connected to by mosaik) are represented by *SimProxy*
objects so that they all look the same to the other components of mosaik:

.. image:: /_static/simmanager.*
   :width: 530
   :align: center
   :alt: The sim manager can import Python simulators, can start simulators as
         sub-processes and can connect to running instances of a simulator.

The sim manager gets its configuration via the :class:`~mosaik.scenario.World`\
’s *sim_config* argument. The *sim_config* is a dictionary containing simulator
names and description of how to start them:

.. code-block:: python

   >>> import mosaik
   >>>
   >>> sim_config = {
   ...     'SimA': {
   ...         'python': 'package.module:SimClass',
   ...     },
   ...     'SimB': {
   ...         'cmd': 'java -jar simB.jar %(addr)s',
   ...         'cwd': 'simB/dist/',
   ...     },
   ...     'SimC': {
   ...         'connect': 'localhost:5678',
   ...     },
   ... }
   >>>
   >>> world = mosaik.World(sim_config)

In the example above, we declare three different simulators. You can freely
choose a name for a simulator. Its configuration should either contain
a *python*, *cmd* or *connect* entry:

*python*
  This tells mosaik to run the simulator in process. As a value, you need to
  specify the module and class name of the simulator separated by a colon.
  In the example, mosaik will ``import package.module`` and instantiate ``sim
  = package.module.SimClass()``. This only works for simulators written in
  Python 3.

*cmd*
  This tells mosaik to execute the specified command *cmd* in order to start a
  new sub-process for the simulator.

  In order to create a socket connection to mosaik the simulator needs to know
  the address of mosaik's server socket. Mosaik will pass this address (in the
  form ``host:port``) as a command line argument, so you need to include the
  placeholder ``%(addr)s`` in your command. Mosaik will replace this with the
  actual address.

  You can optionally specify a current working directory *(cwd)*. If it is
  present, mosaik will change to that directory before executing *cmd*. Its
  default value is ``'.'``.

  In our example, mosaik would execute:

  .. code-block:: bash

     $ cd simB/java
     $ java -jar simB.jar localhost:5555

  in order to start *SimB*.

*connect*
  This tells mosaik to establish a network connection to a running simulator
  instance. It will simply connect to ``host:port`` – ``localhost:5678`` for
  *SimC*
