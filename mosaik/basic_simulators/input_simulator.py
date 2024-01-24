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

FUNCTION_KEY = "Function"
CONSTANT_KEY = "Constant"

META: Meta = {
    "api_version": "3.0",
    "type": "time-based",
    "models": {
        FUNCTION_KEY: {
            "public": True,
            "params": ["function"],
            "attrs": ["value"],
        },
        CONSTANT_KEY: {
            "public": True,
            "params": ["constant"],
            "attrs": ["value"],
        },
    },
    "extra_methods": [],
}


class InputSimulator(mosaik_api_v3.Simulator):
    """
    This simulator gives a steady input to a connected simulator.
    This input can either be an constant numerical value or a custom
    function. It is passed along as parameter in the :meth:`create()` method of this simulator.
    Using the :meth:`get_data()` function, the generated values can be retrieved.
    """

    step_size: int
    functions: Dict[str, Callable[[Time], Any]]
    constants: Dict[str, Any]

    def __init__(self):
        super().__init__(META)
        self.functions = {}
        self.constants = {}
        self.step_size = 1
        self.time = 0

    def init(self, sid: SimId, time_resolution: float = 1, step_size: int = 1) -> Meta:
        self.step_size = step_size
        return self.meta

    def create(
        self, num: int, model: ModelName, **model_params: Any
    ) -> List[CreateResult]:
        new_entities: List[CreateResult] = []
        if model == FUNCTION_KEY:
            for i in range(len(self.functions), len(self.functions) + num):
                new_entities.append(
                    self.create_function_entity(i, model, **model_params)
                )
        elif model == CONSTANT_KEY:
            for i in range(len(self.constants), len(self.constants) + num):
                new_entities.append(
                    self.create_constant_entity(i, model, **model_params)
                )
        return new_entities

    def create_function_entity(
        self, id: int, model: str, function: Callable[[Time], Any]
    ) -> CreateResult:
        eid = f"{FUNCTION_KEY}-{id}"
        self.functions[eid] = function
        return {
            "eid": eid,
            "type": model,
        }

    def create_constant_entity(
        self, id: int, model: str, constant: Any
    ) -> CreateResult:
        eid = f"{CONSTANT_KEY}-{id}"
        self.constants[eid] = constant
        return {"eid": eid, "type": model}

    def step(self, time: Time, inputs: InputData, max_advance: Time) -> Time:
        assert inputs == {}
        self.time = time
        return time + self.step_size

    def get_data(self, outputs: OutputRequest) -> OutputData:
        data: OutputData = {}
        for eid in outputs:
            if CONSTANT_KEY in eid:
                data[eid] = {"value": self.constants[eid]}
            else:
                data[eid] = {"value": self.functions[eid](self.time)}
        return data
