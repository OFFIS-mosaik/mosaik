"""
Mosaik interface for the example simulator.

It more complex than it needs to be to be more flexible and show off various
features of the mosaik API.

"""

import mosaik_api_v3
from loguru import logger

example_sim_meta = {
    "type": "event-based",
    "models": {
        "A": {
            "public": True,
            "params": [],
            "attrs": ["loop_in", "loop_out"],
        },
    },
}


class EchoSim(mosaik_api_v3.Simulator):
    def __init__(self):
        super().__init__(example_sim_meta)
        self.sid = None
        self.eid = None
        self.loop_count = None

    def init(self, sid, time_resolution):
        self.sid = sid
        return self.meta

    def create(self, num, model):
        self.eid = "Echo"
        return [{"eid": self.eid, "type": model}]

    def step(self, time, inputs, max_advance):
        logger.info("step at {time} with inputs {inputs}", time=time, inputs=inputs)
        self.loop_count = list(inputs[self.eid]["loop_in"].values())[0]
        return None

    def get_data(self, outputs):
        return {self.eid: {"loop_out": self.loop_count}}


def main():
    return mosaik_api_v3.start_simulation(EchoSim())
