from pprint import pprint
import mosaik
from mosaik.scenario import SimConfig

# Both simulators are added to the simulation configuration.
SIM_CONFIG: SimConfig = {
    "OutputSim": {
        "python": "output_simulator:OutputSimulator",
    },
    "InputSim": {"python": "input_simulator:InputSimulator"},
}

# The simulation is set to run for 10 steps.
END = 10

# The mosaik world is created.
world = mosaik.World(SIM_CONFIG)


# A sample function for the input simulator.
def sample_function(time: int) -> str:
    # This function takes a Time object as an argument and returns a string.
    return f"The time is {time}"


# START_INCLUDE_SECTION
# The output simulator is initialized.
output_dict = world.start("OutputSim")

# Two entities of the output simulator model are created.
output_model = output_dict.Dict.create(2)

# The input simulator is initialized.
input = world.start("InputSim", step_size=1)

# One function input simulator entity is created.
input_model_func = input.Function.create(1, function=sample_function)

# One constant input simulator entity is created.
input_model_const = input.Constant.create(1, constant=2)

# The input entities are connected to separate output entities
world.connect(input_model_func[0], output_model[1], "value")
world.connect(input_model_const[0], output_model[0], "value")

# Run simulation.
world.run(until=END)

# Dictionary content is printed.
pprint(output_dict.get_dict(output_model[0].eid))
pprint(output_dict.get_dict(output_model[1].eid))
# END_INCLUDE_SECTION
