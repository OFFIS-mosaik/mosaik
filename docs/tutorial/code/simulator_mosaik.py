# simulator_mosaik.py
"""
Mosaik interface for the example simulator.

"""
import mosaik_api

import simulator


META = {
    'models': {
        'ExampleModel': {
            'public': True,
            'params': ['init_val'],
            'attrs': ['delta', 'val'],
        },
    },
}


class ExampleSim(mosaik_api.Simulator):
    def __init__(self):
        super().__init__(META)
        self.simulator = simulator.Simulator()
        self.eid_prefix = 'Model_'
        self.entities = {}  # Maps EIDs to model indices in self.simulator

    def init(self, sid, eid_prefix=None):
        if eid_prefix is not None:
            self.eid_prefix = eid_prefix
        return self.meta

    def create(self, num, model, init_val):
        next_eid = len(self.entities)
        entities = []

        for i in range(next_eid, next_eid + num):
            eid = '%s%d' % (self.eid_prefix, i)
            self.simulator.add_model(init_val)
            self.entities[eid] = i
            entities.append({'eid': eid, 'type': model})

        return entities

    def step(self, time, inputs):
        # Get inputs
        deltas = {}
        for eid, attrs in inputs.items():
            for attr, values in attrs.items():
                model_idx = self.entities[eid]
                new_delta = sum(values.values())
                deltas[model_idx] = new_delta

        # Perform simulation step
        self.simulator.step(deltas)

        return time + 60  # Step size is 1 minute

    def get_data(self, outputs):
        models = self.simulator.models
        data = {}
        for eid, attrs in outputs.items():
            model_idx = self.entities[eid]
            data[eid] = {}
            for attr in attrs:
                if attr not in self.meta['models']['ExampleModel']['attrs']:
                    raise ValueError('Unknown output attribute: %s' % attr)

                # Get model.val or model.delta:
                data[eid][attr] = getattr(models[model_idx], attr)

        return data


def main():
    return mosaik_api.start_simulation(ExampleSim())


if __name__ == '__main__':
    main()
