import mosaik


# Sim config. and other parameters
SIM_CONFIG = {
    'ExampleSim': {
        'python': 'simulator_mosaik:ExampleSim',
        # 'cmd': 'python -m simulator_mosaik %(addr)s',
    },
    'HDF5': {
        'cmd': 'mosaik-hdf5 %(addr)s',
    },
}
END = 10 * 60  # 10 minutes

# Create World
world = mosaik.World(SIM_CONFIG)

# Start simulators
examplesim = world.start('ExampleSim', eid_prefix='Model_')
hdf5 = world.start('HDF5', step_size=60, duration=END)

# Instantiate models
model = examplesim.ExampleModel(init_val=2)
db = hdf5.Database(filename='demo_1.hdf5')

# Connect entities
world.connect(model, db, 'val', 'delta')

# Run simulation
world.run(until=END)