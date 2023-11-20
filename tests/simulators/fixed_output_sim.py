from typing import Any, Dict
import mosaik_api_v3
from mosaik_api_v3.types import InputData, OutputData, OutputRequest
import copy


sim_meta = {
    "type": "time-based",
    "models": {
        "Entity": {
            "public": True,
            "params": ["outputs"],
            "attrs": ["out"],
        },
    },
}


class FixedOutputSim(mosaik_api_v3.Simulator):
    entities: Dict[str, Dict[int, Any]]

    def __init__(self):
        super().__init__(copy.deepcopy(sim_meta))
        self.sid = None
        self.entities = {}
        self.step_size = None

    def init(self, sid: str, time_resolution: float = 1.0):
        self.sid = sid
        return self.meta

    def create(self, num: int, model: str, outputs: Dict[int, Any]):
        n_entities = len(self.entities)
        new_entities = [f"E{i}" for i in range(n_entities, n_entities + num)]
        self.entities.update({entity: outputs for entity in new_entities})
        return [{"eid": eid, "type": model} for eid in new_entities]

    def step(self, time: int, inputs: InputData, max_advance: int):
        self.time = time
        return time + 1

    def get_data(self, outputs: OutputRequest) -> OutputData:
        return {
            entity: {"out": outputs[self.time]}
            for entity, outputs in self.entities.items()
        }


if __name__ == "__main__":
    mosaik_api_v3.start_simulation(FixedOutputSim())
