.. _set-external-events:

===================
Set external events
===================

This tutorial gives an example on how to set external events for integrating unforeseen
interactions of an external system in soft real-time simulation with ``rt_factor=1.0``.
A typical use case for this feature would be Human-in-the-Loop simulations to support human interactions, e.g., control actions.
In mosaik, such external events can be implemented via the the asynchronous ``set_event`` method.
These events will then be scheduled for the next simulation time step.

To give an example of external events in mosaik, a new scenario is created that includes a controller to set external events. 
In addition to the controller, a graphical user interface (GUI) is implemented and started in a subprocess for external control actions by the user.

The example code and additional requirements are shown in the following.

Requirements
====================
First of all, we need to install some additional requirements within the virtual environment
(see :doc:`installation guide </installation>` for setting up a virtual environment)

* pyzmq (https://zeromq.org/languages/python/)
* PyQt5 (https://pypi.org/project/PyQt5/)

.. code-block:: bash

   $ pip install pyzmq PyQt5


Set-event controller
==============================

Next, we need to create a new python module for the set-event controller, e.g., ``controller_set_event.py``.

In the meta data dictionary of the set-event controller, we specify that this is an event-based simulator.

.. literalinclude:: code/controller_set_event.py
   :lines: 1-21

The set-event controller subscribes to external events from the GUI via a `zeromq <https://zeromq.org>`_ subscriber socket
using the `publish-subscribe pattern <https://zeromq.org/socket-api/#publish-subscribe-pattern>`_.
Herefore, a listener thread is created which receives external event messages from the GUI.
More information about the listener thread can be found in the next section.

.. literalinclude:: code/controller_set_event.py
   :lines: 32-60

In order to set the event for the next time step, it is necessary to determine the current simulation time in wall clock time.
For this, we need to store the initial timestamp in :meth:`step()` once for the first simulation step.

.. literalinclude:: code/controller_set_event.py
   :lines: 62-72


Listener thread
===============

The listener thread can be included in the same file as the set-event controller: ``controller_set_event.py``.

The object of the controller class needs to be passed as a parameter to the ``listen_to_external_events`` function, 
which is called as a thread via the defined decorator ``@threaded``.
The listener thread listens to external event messages from the GUI. Once a message arrives,
the listener thread calls the ``set_event`` method to set an external event for the next simulation step in mosaik.

.. literalinclude:: code/controller_set_event.py
   :lines: 24-29
   
.. literalinclude:: code/controller_set_event.py
   :lines: 75-98


Graphical user interface
====================================

For the GUI, we create a new python module, e.g., ``gui_button.py``.

The GUI is created with `PyQt5 <https://pypi.org/project/PyQt5/>`_ and provides a button to set external events in mosaik every time we click on it.
To enable the set-event controller to perform this control action, a `zeromq <https://zeromq.org>`_ publisher socket is used
to send a message to the controller's subscriber that the button has been clicked.

.. figure:: /_static/demo_4.*
   :width: 200
   :align: center
   :alt: GUI for setting external events in mosaik

.. literalinclude:: code/gui_button.py
   :lines: 1-42


Scenario
========

Next, we need to create a new python script for the external events scenario, e.g., ``demo_4.py``.

For this scenario, the set-event controller is added to the ``SIM_CONFIG`` of the scenario.

.. literalinclude:: code/demo_4.py
   :lines: 1-17

The set-event controller is started and initialized. Here, an initial event is added to the set-event controller
so that the controller is executed at ``time=0`` to set the initial timestamp. This is needed for the determination of the current simulation time.

.. literalinclude:: code/demo_4.py
   :lines: 19-24

The GUI is started in a subprocess and must be manually closed after the simulation is completed.

.. literalinclude:: code/demo_4.py
   :lines: 26-27

In order to run the simulation scenario in soft real-time, the ``rt_factor`` is set to ``1.0``.

.. literalinclude:: code/demo_4.py
   :lines: 29-30

Finally, we can run the scenario script as follows:

.. code-block:: bash

   $ python demo_4.py

The printed output shows when the external events are triggered (button was clicked) and executed during simulation.

.. literalinclude:: code/demo_4_example_output.txt
   :lines: 1-37

