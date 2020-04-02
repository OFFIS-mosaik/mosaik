"""
Mosaik interface for the example simulator.

It more complex than it needs to be to be more flexible and show off various
features of the mosaik API.

"""
import logging

import mosaik_api

from example_sim import simulator


logger = logging.getLogger('example_sim')


example_sim_meta = {
    'models': {
        'A': {
            'public': True,
            'params': ['init_val'],
            'attrs': ['val_out', 'dummy_out'],
            'messages': ['message_out'],
        },
        'B': {
            'public': True,
            'params': ['init_val'],
            'attrs': ['val_in', 'val_out', 'dummy_in'],
            'messages': ['message_in'],
        },
        'C': {  # Doesn't actually exist. Used for testing.
            'public': False,
        },
    },
    'extra_methods': [
        'example_method',
    ],
}


class ExampleSim(mosaik_api.Simulator):
    def __init__(self):
        super(ExampleSim, self).__init__(example_sim_meta)
        self.step_size = None
        self.simulators = []
        self.value = None  # May be set in example_method()

    def init(self, sid, step_size=1, self_steps=True):
        self.sid = sid
        self.step_size = step_size
        self.self_steps = self_steps
        return self.meta

    def create(self, num, model, init_val):
        sim_id = len(self.simulators)
        sim = simulator.Simulator(model, num, init_val)
        self.simulators.append(sim)
        return [{'eid': '%s.%s' % (sim_id, eid), 'type': model, 'rel': []}
                for eid, inst in enumerate(sim.instances)]

    def step(self, time, inputs):
        self.inputs = inputs
        for sid, sim in enumerate(self.simulators):
            sim_inputs = [None for i in sim.instances]
            for i, _ in enumerate(sim_inputs):
                eid = '%s.%s' % (sid, i)
                if eid in inputs:
                    sim_inputs[i] = sum(inputs[eid]['val_in'].values())

            for i in range(self.step_size):
                sim.step(sim_inputs)

        if self.self_steps:
            return time + self.step_size
        else:
            return None

    def get_data(self, outputs):
        data = {}
        for eid, attrs in outputs.items():
            sid, idx = map(int, eid.split('.'))
            data[eid] = {}
            value = self.simulators[sid].results[idx]
            for attr in attrs:
                if attr == 'val_out' or (attr == 'message_out' and value > 5):
                    data[eid][attr] = value
                elif attr == 'message_in':
                    print('get message_in', self.inputs)
                    values = self.inputs[eid].get('message_in', {}).values()
                    if values:
                        data[eid][attr] = list(values)[0]
        return data

    def example_method(self, value):
        self.value = value
        return value


def main():
    return mosaik_api.start_simulation(ExampleSim())
