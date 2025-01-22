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
from typing_extensions import override

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
    This input can either be an constant value or given by a custom
    function based on the current time.

    When starting the simulator, a custom step size may be provided
    using the `step_size` parameter. The default is 1.

    When creating a `Constant` entity, the constant must be passed as
    the parameter `constant`.

    When creating a `Function` entity, a function should be passed as
    the `function` parameter. This function should take the current
    mosaik time and return the desired value. This type of entity only
    works when the simulator is started using the `"python"` method.

    In either case, the entity will produce its output on the *value*
    attribute.
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

    @override
    def init(self, sid: SimId, time_resolution: float = 1, step_size: int = 1) -> Meta:
        self.step_size = step_size
        return self.meta

    @override
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

    @override
    def step(self, time: Time, inputs: InputData, max_advance: Time) -> Time:
        assert inputs == {}
        self.time = time
        return time + self.step_size

    @override
    def get_data(self, outputs: OutputRequest) -> OutputData:
        data: OutputData = {}
        for eid in outputs:
            if CONSTANT_KEY in eid:
                data[eid] = {"value": self.constants[eid]}
            else:
                data[eid] = {"value": self.functions[eid](self.time)}
        return data
