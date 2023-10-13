===============
Plotting graphs
===============

Sometimes it is useful to visualize your scenario to understand the behavior of mosaik. You can use the plotting functions in `utils` for different graphs. The parameters are always the same: the world object and the name of the folder where the figures shall be stored in.

Optional parameters are `slice` (see below) and `show_plot` (default: True). With `show_plot` you can control if a window is opened to show the plot in an interactive window. If set to false, the plot is stored directly. If set to true, you can interact with the plot and the chosen view in stored after you close the window.

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
    :emphasize-lines: 30,31,32,33

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
    world.connect(model, model2, 'val', 'delta', initial_data={"val": 1, "delta": 1}, time_shifted=True, weak=True)
    world.connect(model, monitor, 'val', 'delta')

    # Create more entities
    more_models = examplesim.ExampleModel.create(2, init_val=3)
    mosaik.util.connect_many_to_one(world, more_models, monitor, 'val', 'delta')

    # Run simulation
    world.run(until=END)

    mosaik.util.plot_dataflow_graph(world, folder='util_figures')
    #mosaik.util.plot_execution_graph(world, folder='util_figures')
    #mosaik.util.plot_execution_time(world, folder='util_figures')
    #mosaik.util.plot_execution_time_per_simulator(world, folder='util_figures')

Dataflow graph
==============
The dataflow graph shows the direction of the dataflow between the simulators. In the example below, 
the ExampleSim simulator sends data to the Collector. The ExampleSim2 sends data to ExampleSim. The 
dataflow connection from ExampleSim to ExampleSim2 is both weak (dotted line) and timeshifted (red line), 
which can be seen in the red label.

.. figure:: /_static/graphs/dataflowGraph_timeshifted_weak.png
   :width: 100%
   :align: center
   :alt: Dataflow Graph timeshifted weak

Execution graph
===============
The execution graph shows the order in which the simulators are executed. Differing from the example above,
the connection between ExampleSim and ExampleSim2 is only marked as weak, not as timeshifted. 

.. figure:: /_static/graphs/execution_graph_weak.png
   :width: 100%
   :align: center
   :alt: Execution graph weak


If we add back the timeshift parameter, we get an additional arrow from ExampleSim to ExampleSim2. That 
is because the data from ExampleSim is used in ExampleSim2 in a timeshifted manner, i.e., from the previous 
step. This is the :doc:`Gauss-Seidel scheme<../scheduler#cyclic-data-flows>`.

.. figure:: /_static/graphs/execution_graph_timeshifted_weak.png
   :width: 100%
   :align: center
   :alt: Execution graph weak timeshifted

Execution time
==============
The execution time graph shows the execution time of the different simulators so that it can be seen 
where the simulation takes more or less time. In the example below it can be seen that the Collector 
uses comparatively more time than the ExampleSim simulators.

.. figure:: /_static/graphs/executiontime.png
   :width: 100%
   :align: center
   :alt: Execution time

Execution time per simulator
============================
The execution time can also be plotted over the simulation steps per simulator, as can be seen 
in the figure below.

.. figure:: /_static/graphs/execution_time_simulator.png
   :width: 100%
   :align: center
   :alt: Execution time per simulator

Slicing the graphs
==================
If you are especially interested in a certain part of the simulation to be shown you can slice the 
time steps for the execution graph, the execution time graph, and the execution time per simulator. 
You can use the slicing as with Python list slicing. Jumps are not possible. Below you can see 
a few examples:

.. code-block:: Python

    mosaik.util.plot_execution_graph(world, folder='util_figures', slice=[-5,-1])
    mosaik.util.plot_execution_time(world, folder='util_figures', slice=[0,5])
    mosaik.util.plot_execution_time_per_simulator(world, folder='util_figures', slice=[-4,-1])

Below is the execution graph sliced as shown in the example code above.

.. figure:: /_static/graphs/execution_graph_timeshifted_weak_sliced.png
   :width: 100%
   :align: center
   :alt: Execution graph weak timeshifted sliced