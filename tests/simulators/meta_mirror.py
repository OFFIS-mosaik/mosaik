import mosaik_api_v3


class MetaMirror(mosaik_api_v3.Simulator):
    """
    This is a simulator for mocking different sim metas. It will simply
    return the meta that it receives as part of its init call.
    """
    def create(self, num, model, **model_params):
        raise NotImplementedError()

    def __init__(self):
        super().__init__(meta={})
    
    def init(self, sid, meta, time_resolution=1.0):
        self.meta.update(meta)
        return self.meta

    def step(self, time, inputs, max_advance=None):
        raise NotImplementedError()

    def get_data(self, attrs):
        raise NotImplementedError()

    def finalize(self):
        pass
