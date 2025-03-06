==============================================
Pausing and resuming a simulation in mosaik
==============================================

.. currentmodule:: mosaik.scenario

In some scenarios, you may want to **pause** and **resume** a running simulation.
For instance, this feature can be useful when wanting to inspect intermediate
results without terminating the simulation or when using graphical
display tools (e.g. WebVis). mosaik provides a simple mechanism to pause and resume
a simulation using an :class:`~asyncio.Event`.

This guide will walk you through setting up a simulation that can be controlled via keyboard input. 
Pressing ``p`` will pause the simulation, and pressing ``r`` will resume it.

Step 1: Setting up the simulation
----------------------------------

To begin, we need to define a function to start our simulation.
We create a :class:`~World`, which represents our simulation, and define the simulators we want to use.
We also introduce an :class:`~asyncio.Event` called ``event``, which we will later use to control pausing and resuming.

.. literalinclude:: code/pause_resume_how_to.py
   :start-at: Simulation set up
   :end-before: End: Simulation set up

Step 2: Creating and connecting simulators
------------------------------------------

Next, we create instances of the simulators. In this example:

- **OutputSim** generates output values.
- **InputSim** provides input data.

We also connect the simulators so that data flows between them.

.. literalinclude:: code/pause_resume_how_to.py
   :start-at: Simulator set up
   :end-before: End: Simulator set up

Step 3: Handling keyboard input
-------------------------------

To allow users to pause and resume the simulation interactively, we use the 
`pynput <https://pynput.readthedocs.io/en/latest/>`_ module to listen for key presses.

- Pressing ``p`` pauses the simulation by **clearing** the event.
- Pressing ``r`` resumes it by **setting** the event.

.. literalinclude:: code/pause_resume_how_to.py
   :start-at: Keyboard input
   :end-before: End: Keyboard input

Step 4: Running the simulation in a separate thread
---------------------------------------------------

Since mosaik simulations are asynchronous, we need to run them in a separate thread.
We also start the keyboard listener in the main thread to capture user input.
The asyncio event loop and the event itself are aquired from the mosaik thread by
using a queue that was previously given to it during startup.

.. literalinclude:: code/pause_resume_how_to.py
   :start-at: Start keyboard listener and mosaik in different threads
   :end-before: End: Start keyboard listener and mosaik in different threads

Addendum: Pausing automatically at a certain simulation step
------------------------------------------------------------

Instead of hitting the ``p`` key to pause, we could also use the 
``pause_step`` variable of :class:`~World` to determine at what step the simulation
should pause. 

.. code-block:: python

    world.pause_step = 150

Using this line of code before starting the mosaik thread would result in a pause at step 150 in the simulation.
If we use the keyboard listener from step 3, we can simply resume by pressing
``r``.

Full code
----------

.. literalinclude:: code/pause_resume_how_to.py

