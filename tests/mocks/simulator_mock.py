import mosaik_api


class SimulatorMock(mosaik_api.Simulator):
    def create(self, num, model, **model_params):
        raise NotImplementedError()

    def __init__(self, stype='time-based'):
        super().__init__(meta={})
        self.type = stype
        self.finalized = False
        self.meta['type'] = stype
        self.meta['old-api'] = True

    def step(self, time, inputs):
        if self.type == 'time-based':
            return 1
        else:
            return None

    def get_data(self, attrs):
        return {'0': {'x': 0, 'y': 1}}

    def finalize(self):
        self.finalized = True
