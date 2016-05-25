# demo_1.py
import mosaik
import mosaik.util


# Sim config. and other parameters
SIM_CONFIG = {
    'ExampleSim': {
        'python': 'simulator_mosaik:ExampleSim',
    },
    'Collector': {
        'cmd': 'python collector.py %(addr)s',
    },
}
END = 10 * 60  # 10 minutes

# Create World
world = mosaik.World(SIM_CONFIG)

# Start simulators
examplesim = world.start('ExampleSim', eid_prefix='Model_')
collector = world.start('Collector', step_size=60)

# Instantiate models
model = examplesim.ExampleModel(init_val=2)
monitor = collector.Monitor()

# Connect entities
world.connect(model, monitor, 'val', 'delta')

# Create more entities
more_models = examplesim.ExampleModel.create(2, init_val=3)
mosaik.util.connect_many_to_one(world, more_models, monitor, 'val', 'delta')

# Run simulation
world.run(until=END)
