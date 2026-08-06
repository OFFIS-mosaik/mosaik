==============================================
Pausing and resuming a simulation in mosaik
==============================================

.. currentmodule:: mosaik.scenario

In some scenarios, you may want to pause and resume a running simulation.
For instance, this feature can be useful when wanting to inspect intermediate results without terminating the simulation or when using graphical display tools (e.g. WebVis).
mosaik provides a simple mechanism to pause and resume a simulation using an :class:`~asyncio.Event`.

This guide will walk you through setting up a simulation that can be controlled via keyboard input.
Pressing ``p`` will pause the simulation, and pressing ``r`` will resume it.

Step 1: Setting up the simulation
----------------------------------

To begin, we need to define a function to start our simulation.
We create a :class:`~mosaik.async_scenario.AsyncWorld`, which represents our simulation, and define the simulators we want to use.
We also use an :class:`~asyncio.Event` called ``world.running``, which we will later use to control pausing and resuming.

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

To allow users to pause and resume the simulation interactively, we use the `pynput <https://pynput.readthedocs.io/en/latest/>`_ library to listen for key presses.

- Pressing ``p`` pauses the simulation by clearing the event.
- Pressing ``r`` resumes it by setting the event.

.. literalinclude:: code/pause_resume_how_to.py
   :start-at: Keyboard input
   :end-before: End: Keyboard input

Step 4: Running the simulation in a separate thread
---------------------------------------------------

Since we want user inputs to arrive on the main thread to be computed by the listener, we need to start mosaik in a separate thread.
The asyncio event loop and the event itself are acquired from the mosaik thread by using a queue that was previously given to it during startup.

.. literalinclude:: code/pause_resume_how_to.py
   :start-at: Start keyboard listener and mosaik in different threads
   :end-before: End: Start keyboard listener and mosaik in different threads


Full code
----------

.. literalinclude:: code/pause_resume_how_to.py

Addendum: Pausing automatically at a certain simulation step
------------------------------------------------------------

Instead of hitting the ``p`` key to pause, we could also set a certain step number the simulation should stop at.
This could be used for debugging purposes or analysis of a certain intermediate state of the simulation.

To accomplish this, we can get the ProgressProxy object from one of the participating simulators

.. literalinclude:: code/pause_resume_with_set_pause_step.py
   :start-at: get progress
   :end-before: End: get progress

and write a small method that clears the asyncio event, pausing the simulation.

.. literalinclude:: code/pause_resume_with_set_pause_step.py
   :start-at: pause_sim_method
   :end-before: End: pause_sim_method

We can then set the pause_step variable to a valid step within our maximum simulation step range and it will pause when reaching that step.
If we use the keyboard listener from step 3, we can simply resume by pressing ``r``.

The full code for this example looks as follows.

.. literalinclude:: code/pause_resume_with_set_pause_step.py
