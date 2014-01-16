"""
This module provides the interface for users to create simulation scenarios for
mosaik.

The :class:`Environment` holds all necessary data for the simulation and allows
the user to start simulators. It provides a :class:`ModelFactory` (and
a :class:`ModelMock`) via which the user can instantiate model instances
(*entities*). The function :func:`run()` finally starts the simulation.

"""
import itertools

from mosaik import simmanager
from mosaik import simulator


def run(env, until):
    """Start the simulation of *env* until the simulation time *until* is
    reached.

    Return the current simulation time (>= *until*).

    """
    return simulator.run(env, until)


class Environment:
    """The environment holds all data required to specify and run the scenario.

    It provides a method to start a simulator process (:meth:`start()`) and
    manages the simulator instances.

    You have to provide a *sim_config* which tells the environment which
    simulators are available and how to start them. See
    :func:`mosaik.simmanager.start()` for more details.

    """
    def __init__(self, sim_config):
        self.sim_config = sim_config
        """The config dictionary that tells mosaik how to start a simulator."""
        self.sims = {}
        """A dictionary of already started simulators instances."""

        self._sim_ids = {}  # Contains ID counters for each simulator type.

    def start(self, sim_name):
        """Start the simulator named *sim_name* and return a
        :class:`ModelFactory` for it.

        """
        sim = simmanager.start(sim_name, self.sim_config)
        counter = self._sim_ids.setdefault(sim_name, itertools.count())
        sim_id = '%s-%s' % (sim_name, next(counter))
        self.sims[sim_id] = sim
        return ModelFactory(sim_id, sim)


class ModelFactory:
    """This is a facade for a simulator *sim* with ID *sim_id* that allows the
    user to create new model instances (entities) within that simulator.

    For every model that a simulator publicly exposes, the ``ModelFactory``
    provides a :class:`ModelMock` attribute that actually creates the entities.

    If you access an attribute that is not a model or if the model is not
    marked as *public*, an :exc:`AttributeError` is raised.

    """
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
    """Instances of this class are exposed as attributes of
    :class:`ModelFactory` and allow the instantiation of simulator models.

    You can *call* an instance of this class to create exactly one entiy:
    ``sim.ModelName(x=23)``. Alternatively, you can use the :meth:`create()`
    method to create multiple entities with the same set of parameters at once:
    ``sim.ModelName.create(3, x=23)``.

    """
    def __init__(self, name, sim_id, sim):
        self._name = name
        self._sim_id = sim_id
        self._sim = sim

    def __call__(self, **model_params):
        """Call :meth:`create()` to create 1 entity."""
        # TODO: Generate proper signature based on the meta data?
        return self.create(1, **model_params)[0]

    def create(self, num, **model_params):
        """Create *num* entities with the specified *model_params* and return
        a list with the entity dicts.

        The returned list of entities is the same as returned by
        :meth:`mosaik_api.Simulator.create()`, but the simulator is prepended
        to every entity ID to make them globally unique.

        """
        # TODO: Generate proper signature based on the meta data?
        entities = self._sim.create(num, self._name, **model_params)
        for entity in entities:
            entity['eid'] = '%s.%s' % (self._sim_id, entity['eid'])
        return entities
