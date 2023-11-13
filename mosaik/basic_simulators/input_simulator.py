from typing import Any, Callable, Dict, List
import mosaik_api_v3
from mosaik_api_v3.types import (
    CreateResult,
    InputData,
    Meta,
    ModelName,
    OutputData,
    OutputRequest,
    SimId,
    Time,
)

META: Meta = {
    'api_version': '3.0',
    "type": "time-based",
    "models": {
        "Function": {
            "public": True,
            "params": ["function"],
            "attrs": ["value"],
            "any_inputs": False,
            "persistent": ["value"],
            "trigger": [],
        },
        "Constant": {
            "public": True,
            "params": ["constant"],
            "attrs": ["value"],
            "any_inputs": False,
            "persistent": ["value"],
            "trigger": [],
        }
    },
    "extra_methods": [],
}


class InputSimulator(mosaik_api_v3.Simulator):
    step_size: int
    functions: Dict[str, Callable[[Time], Any]]
    constants: Dict[str, int]

    def __init__(self):
        super().__init__(META)

    def init(self, sid: SimId, time_resolution: float = 1, step_size : int =1) -> Meta:
        self.step_size = step_size
        self.functions = {}
        self.constants = {}
        self.function_key = "function"
        self.constant_key = "constant"
        self.time = 0
        return self.meta

    def create(
        self, num: int, model: ModelName, **model_params
    ) -> List[CreateResult]:
        allowed_keys = [self.function_key, self.constant_key]
        model_params_length = 1
        if len(model_params.keys()) != model_params_length or not all(key in allowed_keys for key in model_params.keys()):
            raise ValueError(f"Input needs to be specified to be of the following type: {allowed_keys}")
        for key in model_params.keys():
            if key == "function":
                return self.create_function_entity(num, model, list(model_params.values())[0])
            else:
                return self.create_constant_entity(num, model, list(model_params.values())[0])
        return [{"eid": "ERROR", "type": model}]
    
    def create_function_entity(self, num, model, function):
        new_entities = []
        print("add function")
        for i in range(len(self.functions), len(self.functions) + num):
            eid = f"Function-{i}"
            self.functions[eid] = function
            new_entities.append(
                {
                    "eid": eid,
                    "type": model,
                }
            )
        return new_entities
    
    def create_constant_entity(self, num, model, constant):
        print("add constant")
        new_entities = []
        for i in range(len(self.constants), len(self.constants) + num):
            eid = f"Constant-{i}"
            self.constants[eid] = constant
            new_entities.append(
                {
                    "eid": eid,
                    "type": model,
                }
            )
        return new_entities

    def step(self, time: Time, inputs: InputData, max_advance: Time) -> Time | None:
        assert inputs == {}
        self.time = time
        return time + self.step_size

    def get_data(self, outputs: OutputRequest) -> OutputData:
        const_dict = {}
        func_dict = {}
        for eid in outputs:
            if self.constant_key in eid.lower():
                const_dict[eid] = {"value": self.constants}
            else:
                func_dict[eid] = {"value": self.functions[eid](self.time)}
        return {**const_dict, **func_dict}