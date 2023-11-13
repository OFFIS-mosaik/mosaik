import mosaik_api_v3
from mosaik_api_v3.types import OutputData, OutputRequest

META = {
    'type': 'time-based',
    'extra_methods': ['get_dict'],
    'models': {
        'Dict': {
            'public': True,
            'any_inputs': True,
            'params': [],
            'attrs': [],
        },
    },
}

class OutputSimulator(mosaik_api_v3.Simulator):
    def __init__(self):
        super().__init__(META)
        self.entities = {}  # Maps EIDs to model instances/entities
        self.test_dict = {}

    def init(self, sid, time_resolution, test_dict={}):
        self.test_dict = test_dict
        return self.meta

    def create(self, num, model):
        next_eid = len(self.entities)
        entities = []
        for i in range(next_eid, next_eid + num):
            model_instance = {}
            eid = '%s%d' % (model, i)
            self.entities[eid] = model_instance
            entities.append({'eid': eid, 'type': model})
        return entities

    def step(self, time, inputs, max_advance):
        self.test_dict[time] = inputs
        return time+1
    
    def get_data(self, outputs: OutputRequest) -> OutputData:
        return None

    def get_dict(self):
        return self.test_dict