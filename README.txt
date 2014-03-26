Mosaik
======

Mosaik is a simulation compositor for Smart Grid simulations.

It lets you re-use existing simulators and couple them to simulate large-scale
Smart Grid scenarios. Mosaik offers powerful mechanisms to specify and compose
these scenarios.

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
   ...     exsim1 = world.start('ExampleSim')
   ...     exsim2 = world.start('ExampleSim')
   ...
   ...     a = [exsim1.A(init_val=0) for i in range(3)]
   ...     b = exsim2.B.create(2, init_val=0)
   ...
   ...     for i, j in zip(a, b):
   ...         world.connect(i, j, ('val_out', 'val_in'))
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

Mosaik requires Python >= 3.3. Use `pip`__ to install it, preferably into
a `virtualenv`__::

    $ pip install mosaik

__ http://pip.readthedocs.org/en/latest/installing.html
__ http://virtualenv.readthedocs.org/en/latest/

Documentation, Source code and issues
-------------------------------------

The documentation is available at https://mosaik.readthedocs.org.

Please report bugs and ideas for improvment to our `issue tracker`__.

__ https://bitbucket.org/mosaik/mosaik/issues
