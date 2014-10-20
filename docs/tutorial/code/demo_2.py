# demo_2.py
import mosaik
import mosaik.util


# Sim config. and other parameters
SIM_CONFIG = {
    'ExampleSim': {
        'python': 'simulator_mosaik:ExampleSim',
    },
    'ExampleCtrl': {
        'python': 'controller:Controller',
    },
    'HDF5': {
        'python': 'mosaik_hdf5:MosaikHdf5',
    },
}
END = 10 * 60  # 10 minutes

# Create World
world = mosaik.World(SIM_CONFIG)

# Start simulators
examplesim = world.start('ExampleSim', eid_prefix='Model_')
examplectrl = world.start('ExampleCtrl')
hdf5 = world.start('HDF5', step_size=60, duration=END)

# Instantiate models
models = [examplesim.ExampleModel(init_val=i) for i in range(-2, 3, 2)]
agents = examplectrl.Agent.create(len(models))
db = hdf5.Database(filename='demo_2.hdf5')

# Connect entities
for model, agent in zip(models, agents):
    world.connect(model, agent, ('val', 'val_in'), async_requests=True)

mosaik.util.connect_many_to_one(world, models, db, 'val', 'delta')


# Run simulation
world.run(until=END)
