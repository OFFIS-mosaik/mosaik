from typing import Any, Dict, List

import mosaik_api_v3
from mosaik_api_v3.types import (
    CreateResult,
    Meta,
    ModelName,
    OutputData,
    OutputRequest,
    SimId,
    Time,
)

META: Meta = {
    "api_version": "3.0",
    "type": "event-based",
    "extra_methods": ["set_add_unregistered_attr", "set_add_unregistered_entity"],
    "models": {
        "Test": {
            "public": True,
            "params": [],
            "attrs": ["value", "to_be_deleted"],
        },
    },
}


class WarningsTestSimulator(mosaik_api_v3.Simulator):
    entities: Dict[str, Any]
    add_unregistered_entity: bool
    add_unregistered_attr: bool

    def __init__(self):
        super().__init__(META)
        self.entities = {}
        self.add_unregistered_entity = False
        self.add_unregistered_attr = False

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

    def step(
        self,
        time: Time,
        inputs: Dict[ModelName, Dict[ModelName, Dict[ModelName, Any]]],
        max_advance: Time,
    ) -> Time | None:
        return time + 1

    def get_data(self, outputs: OutputRequest) -> OutputData:
        data: OutputData = {}
        for eid in outputs:
            data[eid] = {"value": self.entities[eid]}
        if self.add_unregistered_entity:
            data["non_existing_eid"] = {"non_existing_attr": self.entities["Test-0"]}
        if self.add_unregistered_attr:
            data["Test-0"]["non_existing_attr"] = self.entities["Test-0"]
        return data

    def set_add_unregistered_entity(self, bool_value):
        self.add_unregistered_entity = bool_value

    def set_add_unregistered_attr(self, bool_value):
        self.add_unregistered_attr = bool_value
