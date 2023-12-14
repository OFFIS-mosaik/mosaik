from mosaik_api_v3 import Meta, SimId, Simulator


class MetaMirror(Simulator):
    """A very simple simulator for testing things related to the meta.
    It will just return the meta given to its init method as its meta.
    """
    def __init__(self):
        super().__init__({})

    def init(self, sid: SimId, meta: Meta, time_resolution: float = 1) -> Meta:
        return meta
