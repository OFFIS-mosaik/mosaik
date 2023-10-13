"""
A generic test simulator for mosaik.

It can be configured in various ways via simulator parameters,
e.g. simulator_a = world.start('A', sim_param1='param1', ..):

step_type : string, {'time-based', 'event-based', 'hybrid'}, default 'time-based')
step_size : int, default=1, only used by time-based simulators
self_steps (dict of {int: int}, default {}), only used by event-based and hybrid simulators
    {step_time: next_step, ..}
    A next step will only be requested (at next_step) for time steps which are
    in self_steps.
wallclock_duration : float, default 0.
    If set, the simulator will sleep for this time (in seconds) during step.
output_timing : dict of {int: int}, optional
    {step_time: output_time, ..}
    If set, output will only be returned at time steps which are in
    output_timing.
    Can also contain a list of output_times: {int: [int, int, ..]} for same time loops
    with multiple steps within the same step_time.
events : dict of {float: int}, default {}
    {real_time: event_time, ..}
    An event will be requested for simulation time event_time after real_time
    seconds.
"""

import mosaik_api_v3
import copy


sim_meta = {
    'type': 'time-based',
    'models': {
        'Entity': {
            'public': True,
            'params': ['outputs'],
            'attrs': ['out'],
        },
    },
}


class FixedOutputSim(mosaik_api_v3.Simulator):
    def __init__(self):
        super().__init__(copy.deepcopy(sim_meta))
        self.sid = None
        self.entities = {}
        self.step_size = None
        self.value = None
        self.event_setter_wait = None

    def init(self, sid, time_resolution):
        self.sid = sid
        return self.meta

    def create(self, num, model, outputs):
        n_entities = len(self.entities)
        new_entities = [f"E{i}" for i in range(n_entities, n_entities + num)]
        self.entities.update({ entity: outputs for entity in new_entities})
        return [{'eid': eid, 'type': model} for eid in new_entities]

    def step(self, time, inputs, max_advance):
        self.time = time
        return time + 1
    
    def get_data(self, outputs):
        return {
            entity: {
                'out': outputs[self.time]
            }
            for entity, outputs in self.entities.items()
        }


if __name__ == '__main__':
    mosaik_api_v3.start_simulation(FixedOutputSim())
