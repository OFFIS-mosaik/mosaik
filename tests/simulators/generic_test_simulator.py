"""
A generic test simulator for mosaik.

"""
import logging

import mosaik_api


logger = logging.getLogger('test_simulator')


sim_meta = {
    'models': {
        'A': {
            'public': True,
            'params': [],
            'attrs': ['val_in', 'val_out'],
        },
    },
}


class TestSim(mosaik_api.Simulator):
    def __init__(self):
        super().__init__(sim_meta)
        self.eid = None
        self.step_size = None
        self.value = None

    def init(self, sid, step_type='discrete-time', step_size=1, self_steps={},
             output_timing=None):
        self.sid = sid
        self.step_type = step_type
        self.meta['type'] = step_type
        self.step_size = step_size
        self.self_steps = self_steps
        self.output_timing = output_timing

        return self.meta

    def create(self, num, model):
        if num > 1 or self.eid:
            raise Exception("Only one entity allowed for TestSim.")
        self.eid = self.sid.lower()
        return [{'eid': self.eid, 'type': model}]

    def step(self, time, inputs):
        self.time = time

        if self.step_type == 'discrete-time':
            return time + self.step_size
        else:
            if time in self.self_steps:
                return {'next_step': self.self_steps[time]}
            else:
                return {}

    def get_data(self, outputs):
        if self.output_timing is None:
            data = {self.eid: {'val_out': self.time}}
        else:
            output_time = self.output_timing.get(self.time, None)
            if output_time is not None:
                data = {'time': output_time, self.eid: {'val_out': self.time}}
            else:
                data = {}
        return data


def main():
    return mosaik_api.start_simulation(TestSim())
