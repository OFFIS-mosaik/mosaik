# controller.py
"""
A simple demo controller.

"""
import mosaik_api


META = {
    'models': {
        'Agent': {
            'public': True,
            'params': [],
            'attrs': ['val_in'],
        },
    },
}


class Controller(mosaik_api.Simulator):
    def __init__(self):
        super().__init__(META)
        self.agents = []

    def create(self, num, model):
        n_agents = len(self.agents)
        entities = []
        for i in range(n_agents, n_agents + num):
            eid = 'Agent_%d' % i
            self.agents.append(eid)
            entities.append({'eid': eid, 'type': model})

        return entities

    def step(self, time, inputs):
        commands = {}
        for eid, attrs in inputs.items():
            values = attrs.get('val_in', {})
            for src, value in values.items():

                if value >= 3:
                    delta = -1
                elif value <= -3:
                    delta = 1
                else:
                    continue

                if eid not in commands:
                    commands[eid] = {}
                if src not in commands[eid]:
                    commands[eid][src] = {}
                commands[eid][src]['delta'] = delta

        yield self.mosaik.set_data(commands)

        return time + 60


def main():
    return mosaik_api.start_simulation(Controller())


if __name__ == '__main__':
    main()
