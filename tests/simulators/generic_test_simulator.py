"""
A generic test simulator for mosaik.

"""
import logging
from time import sleep

if __package__ is None or __package__ == '':
    # uses current directory visibility
    import mosaik_api_set_events as mosaik_api

else:
    # uses current package visibility
    from tests.simulators import mosaik_api_set_events as mosaik_api


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
        self.event_setter_wait = None

    def init(self, sid, step_type='time-based', step_size=1, self_steps={},
             wallclock_duration=0., output_timing=None, events={}):
        self.sid = sid
        self.step_type = step_type
        self.meta['type'] = step_type
        self.step_size = step_size
        self.self_steps = {float(key): val for key, val in self_steps.items()}
        self.wallclock_duration = wallclock_duration
        if output_timing:
            output_timing = {float(key): val
                             for key, val in output_timing.items()}
        self.output_timing = output_timing

        if step_type == 'hybrid':
            self.meta['models']['A']['persistent'] = ['val_out']

        self.events = {float(key): val for key, val in events.items()}
        if events:
            self.meta['set_events'] = True

        return self.meta

    def create(self, num, model):
        if num > 1 or self.eid:
            raise Exception("Only one entity allowed for TestSim.")
        self.eid = self.sid.lower()
        return [{'eid': self.eid, 'type': model}]

    def step(self, time, inputs):
        self.time = time
        if self.wallclock_duration:
            sleep(self.wallclock_duration)

        if self.step_type == 'time-based':
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

    def setup_done(self):
        if self.event_setter_wait:
            self.event_setter_wait.succeed()

    def event_setter(self, env, message):
        last_time = 0
        wait_event = env.event()
        self.event_setter_wait = wait_event
        yield wait_event
        for real_time, event_time in self.events.items():
            yield env.timeout(real_time - last_time)
            yield message.send(["set_event", [event_time], {}])
            last_time = real_time


if __name__ == '__main__':
    mosaik_api.start_simulation(TestSim())
