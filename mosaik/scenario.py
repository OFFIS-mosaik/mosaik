import itertools

from mosaik import simmanager
from mosaik import simulator


def run(env, until):
    return simulator.run(env, until)


class Environment:
    def __init__(self, sim_config):
        self.sim_config = sim_config
        self.sims = {}

        self._sim_ids = {}

    def start(self, sim_name):
        sim = simmanager.start(sim_name, self.sim_config)
        counter = self._sim_ids.setdefault(sim_name, itertools.count())
        sim_id = '%s-%s' % (sim_name, next(counter))
        self.sims[sim_id] = sim
        return ModelFactory(sim_id, sim)


class ModelFactory:
    def __init__(self, sim_id, sim):
        self._sim_id = sim_id
        self._sim = sim
        self._meta = sim.meta
        self._model_cache = {}

    def __getattr__(self, name):
        if name not in self._meta['models']:
            raise AttributeError('Model factory for "%s" has no model "%s"' %
                                 (self._meta['name'], name))
        if not self._meta['models'][name]['public']:
            raise AttributeError('Model "%s" is not public.' % name)

        if name not in self._model_cache:
            self._model_cache[name] = ModelMock(name, self._sim_id, self._sim)

        return self._model_cache[name]


class ModelMock:
    def __init__(self, name, sim_id, sim):
        self._name = name
        self._sim_id = sim_id
        self._sim = sim

    def __call__(self, **model_params):
        # TODO: Generate proper signature based on the meta data?
        return self.create(1, **model_params)[0]

    def create(self, num, **model_params):
        # TODO: Generate proper signature based on the meta data?
        entities = self._sim.create(num, self._name, **model_params)
        for entity in entities:
            entity['eid'] = '%s.%s' % (self._sim_id, entity['eid'])
        return entities

