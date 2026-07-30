from __future__ import annotations

import asyncio
import copy
from typing import Any

import mosaik_api_v3
from mosaik_api_v3.types import InputData, OutputData, OutputRequest

sim_meta: mosaik_api_v3.Meta = {
    "api_version": "3.0",
    "type": "hybrid",
    "models": {
        "Entity": {
            "public": True,
            "params": ["delay"],
            "non-trigger": [],
            "trigger": ["in"],
            "persistent": [],
            "non-persistent": ["out"],
        },
    },
}


class BlockingSim(mosaik_api_v3.Simulator):
    entities: dict[str, dict[int, Any]]

    def __init__(self):
        super().__init__(copy.deepcopy(sim_meta))
        self.sid = None
        self.entities = {}
        self.step_size = None

    def init(self, sid: str, time_resolution: float = 1.0, delay: float = 0.1):
        self.sid = sid
        self.delay = delay
        return self.meta

    def create(self, num: int, model: str):
        n_entities = len(self.entities)
        new_entities = [f"E{i}" for i in range(n_entities, n_entities + num)]
        return [{"eid": eid, "type": model} for eid in new_entities]

    def step(self, time: int, inputs: InputData, max_advance: int):
        yield asyncio.sleep(self.delay)
        self.time = time
        return time + 1

    def get_data(self, outputs: OutputRequest) -> OutputData:
        return {entity: {"out": None} for entity in outputs}
