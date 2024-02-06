|mosaik| basic simulators
=========================

In order to test custom-made simulators, two basic simulators are provided to use and connect to.

- The :class:`~mosaik.basic_simulators.input_simulator.InputSimulator`\ 
  is a simulator that can be used to feed either a constant value or the value of a function into a designated simulator ready to handle the data.
- The :class:`~mosaik.basic_simulators.output_simulator.OutputSimulator`\  writes
  data from a custom simulator into a python dictionary. Users can access this dictionary by calling 
  :meth:`~mosaik.basic_simulators.output_simulator.OutputSimulator.get_dict()`\ on a 
  created output simulator entity.

Below is an example code snippet that connects the input simulator with the output simulator and executes ten time steps.
After the simulation is done, the dictionary including the values received by the input simulator is printed.

.. literalinclude:: code/basic_simulators_example_usage.py
   :start-after: # START_INCLUDE_SECTION
   :end-before: # END_INCLUDE_SECTION

.. _external_components:
