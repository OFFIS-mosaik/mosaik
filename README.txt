Mosaik
======

Mosaik is a simulation compositor for Smart Grid simulations.

It lets you re-use existing simulators and couple them to simulate large-scale
Smart Grid scenarios. Mosaik offers powerful mechanisms to specify and compose
these scenarios.

Version: 2.5.1

License: LGPL

Example
-------

A simple demo scenario with mosaik::

   >>> import mosaik
   >>>
   >>> sim_config = {
   ...     'ExampleSim': {'python': 'example_sim.mosaik:ExampleSim'},
   ... }
   >>>
   >>> def create_scenario(world):
   ...     simulator = world.start('ExampleSim')
   ...
   ...     producers = [simulator.Producer(init_val=0) for _ in range(3)]
   ...     consumers = [simulator.Consumer(init_val=0) for _ in range(3)]
   ...
   ...     for producer, consumer in zip(producers, consumers):
   ...         world.connect(producer, consumer, ('val_out', 'val_in'))
   >>>
   >>> world = mosaik.World(sim_config)
   >>> create_scenario(world)
   >>> world.run(until=2)
   Progress: 25.00%
   Progress: 50.00%
   Progress: 75.00%
   Progress: 100.00%


Installation
------------

Mosaik requires Python >= 3.4. Use `pip`__ to install it, preferably into
a `virtualenv`__::

    $ pip install mosaik

__ http://pip.readthedocs.org/en/latest/installing.html
__ http://virtualenv.readthedocs.org/en/latest/

Documentation, Source Code and Issues
-------------------------------------

The documentation is available at https://mosaik.readthedocs.io.

Please report bugs and ideas for improvement to our `issue tracker`__.

__ https://bitbucket.org/mosaik/mosaik/issues
