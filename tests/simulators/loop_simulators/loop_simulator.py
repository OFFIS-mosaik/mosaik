"""
Mosaik interface for the example simulator.

It more complex than it needs to be to be more flexible and show off various
features of the mosaik API.

"""
import logging

import mosaik_api

logger = logging.getLogger('example_sim')

example_sim_meta = {
    'type': 'hybrid',
    'models': {'A': {'public': True,
                     'params': [],
                     'attrs': ['loop_in', 'loop_out'],
                     'trigger': ['loop_in'],
                     'non-persistent': ['loop_out'],
                     },
               }
}


class LoopSim(mosaik_api.Simulator):
    def __init__(self):
        super().__init__(example_sim_meta)
        self.sid = None
        self.eid = None
        self.step_size = None
        self.self_steps = None
        self.loop_count = 0
        self.loop_length = None

    def init(self, sid, time_resolution, step_size=1, self_steps=None,
             loop_length=0):
        self.sid = sid
        self.step_size = step_size
        self.loop_length = loop_length
        return self.meta

    def create(self, num, model):
        self.eid = 'Loop'
        return [{'eid': self.eid, 'type': model}]

    def step(self, time, inputs, max_advance):
        self.time = time

        self.loop_count += 1

        if self.loop_count == self.loop_length + 1:
            next_step = time + self.step_size
            self.loop_count = 0
        else:
            next_step = None
        print('LOOP STEP', time, next_step )
        return next_step

    def get_data(self, outputs):
        if self.loop_count == 0:
            data = {}
        else:
            data = {self.eid: {'loop_out': self.loop_count}}
        print('LOOP DATA', self.time, data)

        return data


def main():
    return mosaik_api.start_simulation(LoopSim())
