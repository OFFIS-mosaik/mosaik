import mosaik_api


class SimMock(mosaik_api.Simulator):
    def __init__(self):
        super().__init__(meta={})

    def step(self, time, inputs):
        return 1

    def get_data(self, attrs):
        return {'0': {'x': 0, 'y': 1}}
