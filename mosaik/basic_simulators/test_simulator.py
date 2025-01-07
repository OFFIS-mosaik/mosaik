import random
from typing import Any, Dict, List

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

import mosaik
import mosaik.exceptions
import mosaik.util
from mosaik.scenario import SimConfig


META: Meta = {
    "api_version": "3.0",
    "type": "hybrid",
    "extra_methods": ["remove_entity", "remove_attr"],
    "models": {
        "Test": {
            "public": True,
            "params": [],
            "attrs": ["value", "to_be_deleted"],
            "persistent": ["value"],
            "non-persistent": ["to_be_deleted"],
            "trigger": ["to_be_deleted"],
            "non-trigger": ["value"]
        },
    },
}

class TestSimulator(mosaik_api_v3.Simulator):

    entities: Dict[str, Any]

    def __init__(self):
        super().__init__(META)
        self.entities = {}  # Maps EIDs to model instances/entities

    def init(self, sid: SimId, time_resolution: float = 1):
        return self.meta

    def create(
        self, num: int, model: ModelName, **model_params: Any
    ) -> List[CreateResult]:
        next_eid = len(self.entities)
        entities: List[CreateResult] = []
        for i in range(next_eid, next_eid + num):
            entity_value = 0
            eid = f"{model}-{i}"
            self.entities[eid] = entity_value
            entities.append({"eid": eid, "type": model})
        return entities

    def step(self, time: Time, inputs: Dict[ModelName, Dict[ModelName, Dict[ModelName, Any]]], max_advance: Time) -> Time | None:
        return time + 1

    def get_data(self, outputs: OutputRequest) -> OutputData:
        data: OutputData = {}
        for eid in outputs:
            data[eid] = {"value": self.entities[eid]}
        data["non_existing_eid"] = {"non_existing_attr": self.entities["Test-0"]}
        return data

    def remove_entity(self):
        # self.entities.pop(random.choice(list(self.entities.keys())))
        self.entities["test_entity"] = 0

    def remove_attr(self, attr: str):
            META["models"]["Dict"]["attrs"].remove(attr)
