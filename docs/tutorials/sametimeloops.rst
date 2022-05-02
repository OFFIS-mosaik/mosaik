.. _sametimeloops:

===============
Same-time loops
===============

Important use cases for :ref:`same-time loops <same-time_loops>` can be the initialization of simulation and communication between controllers or agents.
As the scenario definition has to provide initialization values for cyclic data-flows and every cyclic data-flow will lead to an incrementing simulation time, it may take some simulation steps until all simulation components are in a stable state, especially, for simulations consisting of multiple physical systems.
The communication between controllers or agents usually takes place at a different time scale than the simulation of the technical systems.
Thus, same-time loops can be helpful to model this behavior in a realistic way.

To give an example of same-time loops in mosaik, the previously shown :doc:`scenario </tutorials/demo2>` is extended with a master controller, which takes control over the other controllers.
The communication between these two layers of controllers will take place in the same step without incrementing the simulation time.
The code of the previous scenario is used as a base and extended as shown in the following.

Master controller
=================

The master controller bases on the code of the :doc:`controller </tutorials/examplectrl>` of the previous scenario.
The first small change for the master controller is in the meta data dictionary, where new attribute names are defined.
The 'delta_in' represent the delta values of the controllers, which will be limited by the master controller.
The results of this control function will be returned to the controllers as 'delta_out'.

.. literalinclude:: code/controller_master.py
   :lines: 9-18

The :meth:`__init__` is extended with ``self.cache`` for storing the inputs and ``self.time`` for storing the current simulation time, which is initialized with 0.

.. literalinclude:: code/controller_master.py
   :lines: 22-27

The :meth:`step()` is changed, so that first the current time is updated in the ``self.time`` variable.
Also the control function is changed.
The master controller gets the delta output of the other controllers as 'delta_in' and stores the last value of each controller in the ``self.cache``.
This is needed, because the controllers are event-based and the current values are only sent if the values changes.
The control function of the master controller limits the sum of all deltas to be ``< 1`` and ``> -1``.
If these limits are exceeded the delta of all controllers will be overwritten by the master controller with ``0`` and sent to the other controller as 'delta_out'.

.. literalinclude:: code/controller_master.py
   :lines: 38-52

Additionally, two small changes in the :meth:`get_data` method were done.
First, the name was updated to 'delta_out' in the check for the correct attribute name.
Second, the current time, which was stored previously in the :meth:`step()`, is added to the output cache dictionary.
This informs mosaik that the simulation should start or stay in a same-time loop if also output data for 'delta_out' is provided.

.. literalinclude:: code/controller_master.py
   :lines: 54-64

Controller
==========

The :doc:`controller </tutorials/examplectrl>` has to be extended to handle the 'delta_out' from the master controller as input.
If it receives an input value for the attribute 'delta', it will not calculate a new delta value, but use the one from the master controller.

.. literalinclude:: code/controller_demo_3.py
   :lines: 38-45

The same-time loop in this scenario will always be finished after the second iteration, because the master controller will overwrite the deltas of the controller and will get back zeros as 'delta_in'.
Thus, it will produce no output in the second iteration and the same-time loop will be finished.

Scenario
========

This scenario is based on the :doc:`previous scenario </tutorials/demo2>`.
In the following description only the changes are explained, but the full code is shown.
The updated controller and the new master controller are added to the sim config of the scenario.

.. literalinclude:: code/demo_3.py
   :lines: 1-23

The master controller is also started and initialized.
The controllers get different 'init_val' values compared to the previous scenario.
Here, it is changed to ``(-2, 0, -2)`` to have the right timing to get into the same-time loop.

.. literalinclude:: code/demo_3.py
   :lines: 25-35

The 'delta' outputs of the controllers are connected to the new master controller and the 'delta_out' of the master controller is connected to the respective controller.
The ``weak=True`` argument defines, that the connection from the controllers to the master controller will be the first to be executed by mosaik.

.. literalinclude:: code/demo_3.py
   :lines: 37-51

The printed output of the collector shows the states of the different simulators.
The collector just shows the final result of the same-time loop and not the steps during the loop.
It can be seen that the 'delta' of 'Agent_1' changes to -1 at time step 2 and at time step 4 all 'delta' attributes are set to 0 by the master controller.

.. literalinclude:: code/demo_3.out
   :lines: 8-25

A visualization of the execution graph shows the data flows in the simulation.
For the first two time steps, only the controllers are executed, as they do not provide any output for 'delta'.
Thus, the master controller was not stepped and the simulation was proceeded directly with the next simulation time step.
At simulation time 2, the master controller is stepped, but as the sum of delta values is not exceeding the limits no control action takes place.
At simulation time 4, the master controller is stepped again and this time sends back a value to the controllers to limit their 'delta' value.
It can be seen, that the controllers are stepped a second time within the same simulation time and send data again to the master controller.
After this second step of the master controller, it does not send an output again and the simulation proceeds to simulation time 5, where the same-time loop occures again.

.. figure:: /_static/demo_3.*
   :width: 600
   :align: center
   :alt: Scheduling of demo 3

   Schedulung of demo 3.
