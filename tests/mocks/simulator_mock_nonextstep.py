import mosaik_api


class SimulatorMockNonextstep(mosaik_api.Simulator):
    def create(self, num, model, **model_params):
        raise NotImplementedError()

    def __init__(self):
        super().__init__(meta={})
        self.finalized = False

    def step(self, time, inputs):
        return None

    def get_data(self, attrs):
        return {'0': {'x': 0, 'y': 1}}

    def finalize(self):
        self.finalized = True
