===============
Plotting graphs
===============

Sometimes it is useful to visualize your scenario to understand the behavior of mosaik. The plotting helpers in ``mosaik.util`` take the world object and a ``folder`` argument that controls where image files are written.

Optional parameters are `slice` (see below) and `show_plot` (default: True). With `show_plot` you can control if a window is opened to show the plot in an interactive window. If set to false, the plot is stored directly. If set to true, you can interact with the plot and the chosen view in stored after you close the window.

There are five different plots available:

.. code-block:: Python

    world = mosaik.World(SIM_CONFIG, debug=True)
    ...
    mosaik.util.plot_df_graph(world, folder='util_figures') (uses Matplotlib)
    mosaik.util.plot_df_graph_groups(world, html_folder='util_figures') (uses Plotly instead of Matplotlib)
    mosaik.util.plot_execution_graph(world, folder='util_figures') (uses Matplotlib)
    mosaik.util.plot_execution_time(world, folder='util_figures') (uses Matplotlib)
    mosaik.util.plot_execution_time_per_simulator(world, folder='util_figures') (uses Matplotlib)

Depending on the function, you need to install either `matplotlib` or `plotly` in your environment beforehand.

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

Plotly dataflow graph with groups
---------------------------------
If you want to highlight simulator groups directly inside the dataflow
graph, use :func:`mosaik.util.plot_df_graph_groups`. The helper
uses `Plotly <https://plotly.com/python/>`_, so install it via ``pip
install plotly`` before running the example below:

.. literalinclude:: code/dataflow_groups.py
   :language: python
   :linenos:

When you open the generated ``dataflow_groups.html`` after running the code above,
you should see a graph similar to the one below.
It shows the group overlays in the background (for example ``North Campus`` and
``North Campus / Solar Farm``) together with the weak dataflow edges.
Set ``show_plot=True`` if you want Plotly to immediately open the figure
while the script is running.

.. figure:: /_static/graphs/group_dataflow_graph_example.png
   :width: 100%
   :align: center
   :alt: Group Dataflow Graph

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
step. This is the :ref:`Gauss-Seidel scheme <cyclic_data_flows>`.

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
in the figure below. You can also set the parameter `plot_per_simulator=True`. In that case,
the plots for the different are separated. This is especially useful if the simulators have 
different step sizes.

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
