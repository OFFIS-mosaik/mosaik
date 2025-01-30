from typing import Any, Dict, cast

import mosaik
import mosaik.basic_simulators
import mosaik.util
from mosaik.scenario import SimConfig


def multiply_by_thousand(p):
    return p * 1000


def multiply_by_ten(p):
    return p * 10


def multiply_by_onehundred(p):
    return p * 100


def test_transform_parameter_input_pulled():
    # Sim config. and other parameters
    SIM_CONFIG: SimConfig = {
        "OutputSim": {
            "python": "mosaik.basic_simulators:OutputSimulator",
        },
        "InputSim": {
            "python": "tests.simulators.generic_test_simulator:TestSim",
        },
    }

    END = 15000  # 15 seconds

    # Create World
    world = mosaik.World(SIM_CONFIG)

    # Start simulators
    output_dict = world.start("OutputSim")
    output_model = output_dict.Dict.create(2)

    input = world.start("InputSim", step_size=1)
    input_model_const = input.A.create(1)

    world.connect(
        input_model_const[0],
        output_model[0],
        ("val_out", "value"),
        transform=multiply_by_thousand,
    )

    world.connect(
        input_model_const[0], output_model[0], "val_out_2", transform=multiply_by_ten
    )

    world.connect(
        input_model_const[0],
        output_model[1],
        ("val_out", "value"),
        transform=multiply_by_onehundred,
    )

    test_dict: Dict[int, Dict[str, Any]] = cast(
        Dict[int, Dict[str, Any]], output_dict.get_dict(output_model[0].eid)
    )
    test_dict2: Dict[int, Dict[str, Any]] = cast(
        Dict[int, Dict[str, Any]], output_dict.get_dict(output_model[1].eid)
    )
    world.run(until=END)
    print(test_dict)
    print(test_dict2)

    assert test_dict != {}
    assert len(test_dict) == END
    for key in test_dict:
        assert test_dict[key]["value"][
            input_model_const[0].full_id
        ] == multiply_by_thousand(key)
        # assert test_dict[key]["val_out_2"][input_model_const[0].full_id] == 10
    for key in test_dict2:
        assert test_dict2[key]["value"][
            input_model_const[0].full_id
        ] == multiply_by_onehundred(key)
test_transform_parameter_input_pulled()

def test_transform_parameter_input_pushed():
    # Sim config. and other parameters
    SIM_CONFIG: SimConfig = {
        "OutputSim": {
            "python": "mosaik.basic_simulators:OutputSimulator",
        },
        "InputSim": {
            "python": "tests.simulators.generic_test_simulator:TestSim",
        },
    }

    END = 15  # 15 seconds

    # Create World
    world = mosaik.World(SIM_CONFIG, cache=False)

    # Start simulators
    output_dict = world.start("OutputSim")
    output_model = output_dict.Dict.create(2)

    input = world.start("InputSim", step_size=1)
    input_model_const = input.A.create(1)

    world.connect(
        input_model_const[0],
        output_model[0],
        ("val_out", "value"),
        transform=multiply_by_thousand,
    )

    world.connect(
        input_model_const[0], output_model[0], "val_out_2", transform=multiply_by_ten
    )

    world.connect(
        input_model_const[0],
        output_model[1],
        ("val_out", "value"),
        transform=multiply_by_onehundred,
    )

    test_dict: Dict[int, Dict[str, Any]] = cast(
        Dict[int, Dict[str, Any]], output_dict.get_dict(output_model[0].eid)
    )
    test_dict2: Dict[int, Dict[str, Any]] = cast(
        Dict[int, Dict[str, Any]], output_dict.get_dict(output_model[1].eid)
    )
    world.run(until=END)
    print(test_dict)
    print(test_dict2)

    assert test_dict != {}
    assert len(test_dict) == END
    for key in test_dict:
        assert test_dict[key]["value"][
            input_model_const[0].full_id
        ] == multiply_by_thousand(key)
        assert test_dict[key]["val_out_2"][input_model_const[0].full_id] == 10
    for key in test_dict2:
        assert test_dict2[key]["value"][
            input_model_const[0].full_id
        ] == multiply_by_onehundred(key)
