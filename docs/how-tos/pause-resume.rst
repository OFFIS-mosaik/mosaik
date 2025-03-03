==============================================
Pausing and Resuming a Simulation in mosaik
==============================================

In some scenarios, you may want to **pause** and **resume** a running simulation.
For instance, this feature can be useful when wanting to inspect intermediate
results without terminating the simulation or when using graphical
display tools (e.g. WebVis). mosaik provides a simple mechanism to pause and resume
a simulation using an :class:`~asyncio.Event`.

This guide will walk you through setting up a simulation that can be controlled via keyboard input. 
Pressing ``p`` will pause the simulation, and pressing ``r`` will resume it.

Step 1: Setting Up the Simulation
----------------------------------

To begin, we need to define a function to start our simulation.
We create a **world**, which represents our simulation, and define the simulators we want to use.
We also introduce an :class:`~asyncio.Event` called ``event``, which we will later use to control pausing and resuming.

.. literalinclude:: code/pause_resume_feature.py
   :start-at: Simulation set up
   :end-before: End: Simulation set up

Step 2: Creating and Connecting Simulators
------------------------------------------

Next, we create instances of the simulators. In this example:

- **OutputSim** generates output values.
- **InputSim** provides input data.

We also connect the simulators so that data flows between them.

.. literalinclude:: code/pause_resume_feature.py
   :start-at: Simulator set up
   :end-before: End: Simulator set up

Step 3: Handling Keyboard Input
-------------------------------

To allow users to pause and resume the simulation interactively, we use the `pynput` library to listen for key presses.

- Pressing ``p`` pauses the simulation by **clearing** the event.
- Pressing ``r`` resumes it by **setting** the event.

.. literalinclude:: code/pause_resume_feature.py
   :start-at: Keyboard input
   :end-before: End: Keyboard input

Step 4: Running the Simulation in a Separate Thread
---------------------------------------------------

Since mosaik simulations are asynchronous, we need to run them in a separate thread.
We also start the keyboard listener in the main thread to capture user input.

.. literalinclude:: code/pause_resume_feature.py
   :start-at: Start keyboard listener and mosaik in different threads
   :end-before: End: Start keyboard listener and mosaik in different threads


Full code
----------

.. literalinclude:: code/pause_resume_feature.py

