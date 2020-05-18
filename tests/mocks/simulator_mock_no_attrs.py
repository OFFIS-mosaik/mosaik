import mosaik_api


class SimulatorMockNoAttrs(mosaik_api.Simulator):
    def create(self, num, model, **model_params):
        raise NotImplementedError()

    def __init__(self):
        super().__init__(meta={'models': {'dummy': {'public': True, 'params': [], 'messages': 'dummy_msg'}}})
        self.finalized = False

    def step(self, time, inputs):
        raise NotImplementedError()

    def get_data(self, attrs):
        raise NotImplementedError()

    def finalize(self):
        self.finalized = True
