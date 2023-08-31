Mosaik
======

Mosaik is a simulation compositor for Smart Grid simulations.

It lets you re-use existing simulators and couple them to simulate large-scale
Smart Grid scenarios. Mosaik offers powerful mechanisms to specify and compose
these scenarios.

Version: 3.2.0

License: LGPL

Example
-------

A simple demo scenario with mosaik::

    >>> import mosaik
    >>> sim_config = {
    ...   'ExampleSim': {'python': 'example_sim.mosaik:ExampleSim'},
    ... }
    >>> def create_scenario(world):
    ...   sim_1 = world.start('ExampleSim')
    ...   sim_2 = world.start('ExampleSim')
    ...   a_set = [sim_1.A(init_val=0) for i in range(3)]
    ...   b_set = sim_2.B.create(2, init_val=0)
    ...   for i, j in zip(a_set, b_set):
    ...     world.connect(i, j, ('val_out', 'val_in'))
    ...
    >>> world = mosaik.World(sim_config)
    >>> create_scenario(world)
    2022-11-21 15:39:48.554 | INFO     | mosaik.scenario:start:255 - Starting "ExampleSim" as "ExampleSim-0" ...
    2022-11-21 15:39:48.555 | INFO     | mosaik.scenario:start:255 - Starting "ExampleSim" as "ExampleSim-1" ...
    >>> world.run(until=2)
    2022-11-21 15:40:05.187 | INFO     | mosaik.scenario:run:532 - Starting simulation.
    100%|█████████████████████████████████████████████████████████████████████████████████| 2/2 [00:00<00:00, 539.56steps/s]
    2022-11-21 15:40:05.193 | INFO     | mosaik.scenario:run:576 - Simulation finished successfully.


Installation
------------

Mosaik requires Python >= 3.8. Use `pip`__ to install it, preferably into
a `virtualenv`__::

    $ pip install mosaik

__ http://pip.readthedocs.org/en/latest/installing.html
__ http://virtualenv.readthedocs.org/en/latest/

Documentation, Source Code and Issues
-------------------------------------

The documentation is available at https://mosaik.readthedocs.io.

Please report bugs and ideas for improvement to our `issue tracker`__.

__ https://gitlab.com/mosaik/mosaik/-/issues

How to cite mosaik
------------------
If you want to cite mosaik, e.g. in a work in which you use mosaik, you can use this publication::

    C. Steinbrink, M. Blank-Babazadeh, A. El-Ama, S. Holly, B. Lüers, M. Nebel-Wenner, R.P. Ramirez Acosta, T. Raub, J.S. Schwarz, S. Stark, A. Nieße, and S. Lehnhoff, “CPES Testing with mosaik: Co-Simulation Planning, Execution and Analysis”, Applied Sciences, vol. 9, no. 5, 2019.

Or as bibtex::
    
    @Article{app9050923,
        AUTHOR = {Steinbrink, Cornelius and Blank-Babazadeh, Marita and El-Ama, André and Holly, Stefanie and Lüers, Bengt and Nebel-Wenner, Marvin and Ramírez Acosta, Rebeca P. and Raub, Thomas and Schwarz, Jan Sören and Stark, Sanja and Nieße, Astrid and Lehnhoff, Sebastian},
        TITLE = {CPES Testing with mosaik: Co-Simulation Planning, Execution and Analysis},
        JOURNAL = {Applied Sciences},
        VOLUME = {9},
        YEAR = {2019},
        NUMBER = {5},
        ARTICLE-NUMBER = {923},
        URL = {https://www.mdpi.com/2076-3417/9/5/923},
        ISSN = {2076-3417},
        DOI = {10.3390/app9050923}
    }

We are hiring!
--------------
You are interested in developing mosaik to be ready for the next challenges in co-simulation to come? 
Feel free to take a look at the open job positions at the `OFFIS Energy division <https://www.offis.de/en/offis/career/vacancies.html>`_.
Currently we have open positions for core mosaik development.