import mosaik

from argparser import argparser

args, world_args, run_args = argparser(N=10000, until=10)

SIM_CONFIG = {
    'ExampleSim': {
        'python': 'example_sim.mosaik:ExampleSim',
    },
}

world = mosaik.World(SIM_CONFIG, **world_args)

a = world.start('ExampleSim', step_size=1).A.create(1, init_val=0)
b = world.start('ExampleSim', step_size=1).B.create(args.N, init_val=0)

for ib in b:
    world.connect(a[0], ib, ('val_out', 'val_in'))

world.run(**run_args)
