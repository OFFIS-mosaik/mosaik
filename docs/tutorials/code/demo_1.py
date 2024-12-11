# demo_1.py
import mosaik
import mosaik.util

# End: Imports


# Sim config
SIM_CONFIG: mosaik.SimConfig = {
    "ExampleSim": {
        "python": "simulator_mosaik:ExampleSim",
    },
    "Collector": {
        "cmd": "%(python)s collector.py %(addr)s",
    },
}
END = 10  # 10 seconds
# End: Sim config

# Create World
world = mosaik.World(SIM_CONFIG)
# End: Create World

# Start simulators
examplesim = world.start("ExampleSim", eid_prefix="Model_")
collector = world.start("Collector")
# End: Start simulators

# Instantiate models
model = examplesim.ExampleModel(init_val=2)
monitor = collector.Monitor()
# End: Instantiate models

# Connect entities
world.connect(model, monitor, "val", "delta")
# End: Connect entities

# Create more entities
more_models = examplesim.ExampleModel.create(2, init_val=3)
mosaik.util.connect_many_to_one(world, more_models, monitor, "val", "delta")
# End: Create more entities

# Run simulation
world.run(until=END)
