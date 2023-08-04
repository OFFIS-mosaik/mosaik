===============
Plotting graphs
===============

Sometimes it is useful to visualize your scenario to understand the behavior of mosaik. You can use the plotting functions in `utils` for different graphs. The parameters are always the same: the world object and the name of the folder where the figures shall be stored in.

There are four different plots available:

.. code-block:: Python
    world = mosaik.World(SIM_CONFIG, debug=True)
    ...
    mosaik.util.plot_df_graph(world, folder='util_figures')
    mosaik.util.plot_execution_graph(world, folder='util_figures')
    mosaik.util.plot_execution_time(world, folder='util_figures')
    mosaik.util.plot_execution_time_per_simulator(world, folder='util_figures')

You need to install `matplotlib` in your environment before using these functions.

Examples
========
The following examples will be done with the following scenario. This code is just to show 
how the connections are set up, so that the graphs can be interpreted accordingly. The
important part is the part where the entities are connected.

.. code-block:: Python
    import mosaik.util


    # Sim config. and other parameters
    SIM_CONFIG = {
        'ExampleSim': {
            'python': 'simulator_mosaik:ExampleSim',
        },
        'ExampleSim2': {
            'python': 'simulator_mosaik:ExampleSim',
        },
        'Collector': {
            'cmd': '%(python)s collector.py %(addr)s',
        },
    }
    END = 10  # 10 seconds

    # Create World
    world = mosaik.World(SIM_CONFIG, debug=True)

    # Start simulators
    examplesim = world.start('ExampleSim', eid_prefix='Model_')
    examplesim2 = world.start('ExampleSim2', eid_prefix='Model2_')
    collector = world.start('Collector')

    # Instantiate models
    model = examplesim.ExampleModel(init_val=2)
    model2 = examplesim2.ExampleModel(init_val=2)
    monitor = collector.Monitor()

    # Connect entities
    world.connect(model2, model, 'val', 'delta')
    world.connect(model, model2, 'val', 'delta', initial_data={"val": "test", "delta": "test"}, time_shifted=True, weak=True)
    world.connect(model, monitor, 'val', 'delta')

    # Create more entities
    more_models = examplesim.ExampleModel.create(2, init_val=3)
    mosaik.util.connect_many_to_one(world, more_models, monitor, 'val', 'delta')

    # Run simulation
    world.run(until=END)

    mosaik.util.plot_df_graph(world, folder='util_figures')
    #mosaik.util.plot_execution_graph(world, folder='util_figures')
    #mosaik.util.plot_execution_time(world, folder='util_figures')
    #mosaik.util.plot_execution_time_per_simulator(world, folder='util_figures')

Dataflow graph
==============
The dataflow graph shows the direction of the dataflow between the simulators. In the example below, 
the ExampleSim simulator sends data to the Collector. The ExampleSim2 sends data to ExampleSim. The 
dataflow connection from ExampleSim to ExampleSim2 is both weak (dotted line) and timeshifted (red line), 
which can be seen in the red label.

.. image:: _static/graphs/dataflowGraph_2_timeshifted_weak.*
  :width: 400
  :alt: Dataflow Graph timeshifted weak

Execution graph
===============
The execution graph shows the order in which the simulators are executed. Differing from the example above,
the connection between ExampleSim and ExampleSim2 is only marked as weak, not as timeshifted. 

.. image:: _static/graphs/execution_graph_weak.png
  :width: 400
  :alt: Execution graph weak


If we add back the timeshift parameter, we get an additional arrow from ExampleSim to ExampleSim2. That 
is because the data from ExampleSim is used in ExampleSim2 in a timeshifted manner, i.e., from the previous 
step. This is the :doc:`Gauss-Seidel scheme<../scheduler>`.

.. image:: _static/graphs/execution_graph_timeshifted_weak.png
  :width: 400
  :alt: Execution graph

Execution time
==============
The execution time graph shows the execution time of the different simulators so that it can be seen 
where the simulation takes more or less time. In the example below it can be seen that the Collector 
uses comparatively more time than the ExampleSim simulators.

.. image:: _static/graphs/executiontime.png
  :width: 400
  :alt: Execution time

Execution time per simulator
============================
The execution time can also be plotted over the simulation steps per simulator, as can be seen 
in the figure below.

.. image:: _static/graphs/execution_time_simulator.png
  :width: 400
  :alt: Execution time per simulator