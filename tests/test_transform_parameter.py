from typing import Any, Dict, cast

import mosaik
import mosaik.basic_simulators
import mosaik.util
from mosaik.scenario import SimConfig


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

    # Start simulators
    output_dict = world.start("OutputSim")
    output_model = output_dict.Dict.create(1)

    input = world.start("InputSim", step_size=1)
    input_model_const = input.Constant.create(1, constant=2)

    multiply_by_thousand = lambda p: p * 1000

    world.connect(
        input_model_const[0], output_model[0], "value", transform=multiply_by_thousand
    )

    test_dict: Dict[int, Dict[str, Any]] = cast(
        Dict[int, Dict[str, Any]], output_dict.get_dict(output_model[0].eid)
    )
    world.run(until=END)
    print(test_dict)

    assert test_dict != {}
    assert len(test_dict) == END
    for key in test_dict:
        assert test_dict[key]["value"][input_model_const[0].full_id] == 2


test_basic_simulators()
