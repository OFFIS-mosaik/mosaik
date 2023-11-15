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
    "api_version": "3.0",
    "type": "time-based",
    "models": {
        "Function": {
            "public": True,
            "params": ["function"],
            "attrs": ["value"],
        },
        "Constant": {
            "public": True,
            "params": ["constant"],
            "attrs": ["value"],
        },
    },
    "extra_methods": [],
}


class InputSimulator(mosaik_api_v3.Simulator):
    step_size: int
    functions: Dict[str, Callable[[Time], Any]]
    constants: Dict[str, int]

    def __init__(self):
        super().__init__(META)

    def init(self, sid: SimId, time_resolution: float = 1, step_size: int = 1) -> Meta:
        self.step_size = step_size
        self.functions = {}
        self.constants = {}
        self.function_key = "Function"
        self.constant_key = "Constant"
        self.time = 0
        return self.meta

    def create(self, num: int, model: ModelName, **model_params) -> List[CreateResult]:
        new_entities = []
        if model == self.function_key:
            for i in range(len(self.functions), len(self.functions) + num):
                new_entities.append(
                    self.create_function_entity(i, model, **model_params)
                )
        elif model == self.constant_key:
            for i in range(len(self.constants), len(self.constants) + num):
                new_entities.append(
                    self.create_constant_entity(i, model, **model_params)
                )
        return new_entities

    def create_function_entity(self, id, model, function):
        eid = f"Function-{id}"
        self.functions[eid] = function
        return {
            "eid": eid,
            "type": model,
        }

    def create_constant_entity(self, id, model, constant):
        eid = f"Constant-{id}"
        self.constants[eid] = constant
        return {"eid": eid, "type": model}

    def step(self, time: Time, inputs: InputData, max_advance: Time) -> Time | None:
        assert inputs == {}
        self.time = time
        return time + self.step_size

    def get_data(self, outputs: OutputRequest) -> OutputData:
        data = {}
        for eid in outputs:
            if self.constant_key in eid:
                data[eid] = {"value": self.constants[eid]}
            else:
                data[eid] = {"value": self.functions[eid](self.time)}
        return data
