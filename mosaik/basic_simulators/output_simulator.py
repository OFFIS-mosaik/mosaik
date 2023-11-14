import mosaik_api_v3
from mosaik_api_v3.types import OutputData, OutputRequest
import mosaik
from mosaik import exceptions as MosaikException

META = {
    "type": "time-based",
    "extra_methods": ["get_dict"],
    "models": {
        "Dict": {
            "public": True,
            "any_inputs": True,
            "params": [],
            "attrs": [],
        },
    },
}

class OutputSimulator(mosaik_api_v3.Simulator):
    def __init__(self):
        super().__init__(META)
        self.entities = {}  # Maps EIDs to model instances/entities
        self.results = {}

    def init(self, sid, time_resolution):
        return self.meta

    def create(self, num, model):
        next_eid = len(self.entities)
        entities = []
        for i in range(next_eid, next_eid + num):
            model_instance = {}
            eid = f"{model}-{i}"
            self.entities[eid] = model_instance
            entities.append({"eid": eid, "type": model})
        return entities

    def step(self, time, inputs, max_advance):
        for entity in self.entities.values():
            entity[time] = inputs
        return time+1
    
    def get_data(self, outputs: OutputRequest) -> OutputData:
        raise MosaikException.ScenarioError("This function is not supposed to be used in this simulator. Use this simulator \n"+
                                            "for input data only.")

    def get_dict(self, eid):
        return self.entities[eid]