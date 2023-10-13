import mosaik_api_v3


class SimulatorMock(mosaik_api_v3.Simulator):
    def create(self, num, model, **model_params):
        raise NotImplementedError()

    def __init__(self, stype='time-based'):
        super().__init__(meta={})
        self.type = stype
        self.finalized = False
        self.meta['type'] = stype

    def init(self, sid, time_resolution=None):
        self.time_resolution = time_resolution
        return self.meta

    def step(self, time, inputs, max_advance=None):
        if self.type == 'time-based':
            return 1
        else:
            return None

    def get_data(self, attrs):
        return {'0': {'x': 0, 'y': 1}}

    def finalize(self):
        self.finalized = True
