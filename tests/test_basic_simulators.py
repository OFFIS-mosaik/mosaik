import mosaik
import mosaik.util
import mosaik.basic_simulators
from mosaik.scenario import SimConfig
from typing import Any, Dict, cast


def test_basic_simulators():
    # Sim config. and other parameters
    SIM_CONFIG: SimConfig = {
        "OutputSim": {
            "python": "mosaik.basic_simulators:OutputSimulator",
        },
        "InputSim": {"python": "mosaik.basic_simulators:InputSimulator"},
    }

    END = 15  # 15 seconds

    # Create World
    world = mosaik.World(SIM_CONFIG)

    def sample_function(time: int) -> str:
        # This function takes a Time object as an argument and returns a string.
        return f"The time is {time}"

    # Start simulators
    output_dict = world.start("OutputSim")
    output_model = output_dict.Dict.create(2)

    input = world.start("InputSim", step_size=1)
    input_model_func = input.Function.create(1, function=sample_function)
    input_model_const = input.Constant.create(2, constant=2)

    world.connect(input_model_func[0], output_model[1], "value")
    world.connect(input_model_const[0], output_model[0], "value")

    # Run simulation
    test_dict: Dict[int, Dict[str, Any]] = cast(
        Dict[int, Dict[str, Any]], output_dict.get_dict(output_model[1].eid)
    )
    test_input_eid = input_model_func[0].sid + "." + input_model_func[0].eid
    print(test_input_eid)
    world.run(until=END)

    assert test_dict != {}
    assert len(test_dict) == END
    for key in test_dict:
        assert test_dict[key]["value"][test_input_eid] == f"The time is {key}"