# demo_2.py
import mosaik
import mosaik.util


# Sim config
SIM_CONFIG = {
    "ExampleSim": {
        "python": "simulator_mosaik:ExampleSim",
    },
    "ExampleCtrl": {
        "python": "controller:Controller",
    },
    "Collector": {
        "cmd": "%(python)s collector.py %(addr)s",
    },
}
END = 10  # 10 seconds

# Create World
world = mosaik.World(SIM_CONFIG)
# End: Create World

# Start simulators
with world.group():
    examplesim = world.start("ExampleSim", eid_prefix="Model_")
    examplectrl = world.start("ExampleCtrl")
collector = world.start("Collector")
# End: Start simulators

# Instantiate models
models = [examplesim.ExampleModel(init_val=i) for i in range(-2, 3, 2)]
agents = examplectrl.Agent.create(len(models))
monitor = collector.Monitor()
# End: Instantiate models

# Connect entities
for model, agent in zip(models, agents):
    world.connect(model, agent, ("val", "val_in"))
    world.connect(agent, model, "delta", weak=True)
# End: Connect entities

# Connect to monitor
mosaik.util.connect_many_to_one(world, models, monitor, "val", "delta")
mosaik.util.connect_many_to_one(world, agents, monitor, "delta")

# Run simulation
world.run(until=END)
