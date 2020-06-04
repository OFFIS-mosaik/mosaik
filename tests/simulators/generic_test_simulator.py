"""
Mosaik interface for the example simulator.

It more complex than it needs to be to be more flexible and show off various
features of the mosaik API.

"""
import logging

import mosaik_api

from time import sleep

logger = logging.getLogger('test_simulator')

test_sim_meta = {'models': {'TestModel':
                                   {'public': True,
                                    'params': ['init_val'],
                                    'attrs': ['inputs', 'last_step'],
                                    'messages': ['message_in', 'last_step_message']
                                    },
                               }
                    }


class TestSimulator(mosaik_api.Simulator):
    def __init__(self):
        super(TestSimulator, self).__init__(test_sim_meta)
        self.step_size = None
        self.self_steps = None
        self.last_self_step = None
        self.stepping = None
        self.entities = {}
        self.message_steps = None
        self.step_duration = None
        self.return_dict = None
        self.wallclock_duration = None

    def init(self, sid, step_size=None, self_steps=None, message_steps=[],
             step_duration=None, return_dict=False, wallclock_duration=0.,
             continuous=True):
        self.sid = sid
        if step_size and self_steps is not None:
            raise Exception
        elif self_steps is not None:
            if self_steps:
                self.stepping = 'custom'
                self.self_steps = self_steps
                self.i_selfstep = 0
            else:
                self.stepping = None
        else:
            self.stepping = 'constant'
            if not step_size:
                step_size = 1
            self.step_size = step_size

        self.message_steps = message_steps
        self.step_duration = step_duration
        self.return_dict = return_dict
        self.wallclock_duration = wallclock_duration

        if not continuous:
            del self.meta['models']['TestModel']['attrs']
        return self.meta

    def create(self, num, model):
        if model != 'TestModel':
            raise Exception('Only model `TestModel` exists!')

        next_eid = len(self.entities)
        entities = []

        for i in range(next_eid, next_eid + num):
            eid = str(i)
            self.entities[eid] = {'inputs': None, 'last_step': None}
            entities.append({'eid': eid, 'type': model})

        return entities

    def step(self, time, inputs):
        if self.wallclock_duration:
            sleep(self.wallclock_duration)
        if self.stepping == 'constant':
            next_step = time + self.step_size
        elif self.stepping == 'custom':
            try:
                next_step = self.self_steps[self.i_selfstep]
                self.i_selfstep += 1
            except IndexError:
                next_step = None
                self.stepping = None
        else:
            next_step = None

        for eid, values in inputs.items():
            if eid not in self.entities:
                raise Exception('Entity {} not in self.entities'.format(eid))

            self.entities[eid]['inputs'] = values

        for entity in self.entities.values():  #TODO: only (self-)stepped entities?
            entity['last_step'] = time
            if time in self.message_steps:
                entity['last_step_message'] = time
            else:
                entity['last_step_message'] = None

        self.last_self_step = next_step

        if self.return_dict:
            return_dict = {}
            if next_step:
                return_dict['next_step'] = next_step
            if self.step_duration:
                return_dict['busy_until'] = time + self.step_duration
                if next_step:
                    assert next_step >= time + self.step_duration, f"next_step must be >= busy_until, but next_step={next_step} and busy_until={time + self.step_duration}"
            return return_dict
        else:
            return next_step

    def get_data(self, outputs):
        data = {}
        for eid, attrs in outputs.items():
            data[eid] = {}
            for attr in attrs:
                if attr not in ['inputs', 'last_step', 'last_step_message']:
                    raise Exception('{} not in attributes'.format(attr))

                if attr != 'last_step_message' or self.entities[eid]['last_step_message'] is not None:
                    data[eid][attr] = self.entities[eid][attr]
        return data


def main():
    return mosaik_api.start_simulation(TestSimulator())


if __name__ == '__main__':
    main()
