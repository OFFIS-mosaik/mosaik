# benchmark_sparse_time.py

from argparser import argparser
import mosaik.util


args, world_args, run_args = argparser(N=10000, until=1000)
run_args['until'] *= args.N

# Sim config. and other parameters
SIM_CONFIG = {
    'ExampleSim': {
        'python': 'tests.simulators.generic_test_simulator:TestSim'
    },
}

# Create World
world = mosaik.World(SIM_CONFIG, **world_args)

# Start simulators und instantiate models:
a = world.start('ExampleSim', step_size=args.N).A()
b = world.start('ExampleSim', step_size=args.N).A()

# Connect entities
world.connect(a, b, ('val_out', 'val_in'))

# Run simulation
world.run(**run_args)
