# demo_1.py
from pprint import pprint
import time
import mosaik
import mosaik.util

# Sim config. and other parameters
SIM_CONFIG = {
    'api_version': 3.0,
    'OutputSim': {
        'python': 'output_simulator:OutputSimulator',
    },
    'InputSim': {
        'python': 'input_simulator:InputSimulator'
    },
}

END = 15  # 15 seconds

test_dict_instance = {'entry1' : 1}

# Create World
world = mosaik.World(SIM_CONFIG)

def sample_function(time: int) -> str:
    # This function takes a Time object as an argument and returns a string.
    return f"The time is {time}"

# Start simulators
output_dict = world.start('OutputSim')
output_model = output_dict.Dict.create(2)

input = world.start('InputSim', step_size=1)
input_model_func = input.Function.create(1, function=sample_function)
input_model_const = input.Constant.create(2, constant=2)


world.connect(input_model_func[0], output_model[1], 'value')
world.connect(input_model_const[0], output_model[0], 'value')

# Run simulation
world.run(until=END)
pprint(output_dict.get_dict(output_model[1].eid))
