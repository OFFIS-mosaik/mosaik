import mosaik_api


class MetaMock(mosaik_api.Simulator):
    """
    This is a simulator for mocking different sim metas. It will simply
    return the meta that it receives as part of its init call.
    """
    def create(self, num, model, **model_params):
        raise NotImplementedError()

    def __init__(self):
        super().__init__(meta={})
    
    def init(self, sid, meta):
        self.meta.update(meta)
        return self.meta

    def step(self, time, inputs):
        raise NotImplementedError()

    def get_data(self, attrs):
        raise NotImplementedError()

    def finalize(self):
        pass