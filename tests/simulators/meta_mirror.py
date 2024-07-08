import mosaik_api_v3


class MetaMirror(mosaik_api_v3.Simulator):
    """
    This is a simulator for mocking different sim metas. It will simply
    return the meta that it receives as part of its init call.
    """
    def create(self, num, model, **model_params):
        return [
            {"eid": f"{model}-{i}", "type": model}
            for i in range(num)
        ]

    def __init__(self):
        super().__init__(meta={})

    def init(self, sid, meta, time_resolution=1.0):
        # Don't call self.meta.update(meta) as usual here because we
        # want to set the exact meta returned to mosaik
        self.meta = meta
        return self.meta

    def step(self, time, inputs, max_advance=None):
        raise NotImplementedError()

    def get_data(self, attrs):
        raise NotImplementedError()

    def finalize(self):
        pass
