"""
This module provides the interface for users to create simulation scenarios for
mosaik.

The :class:`Environment` holds all necessary data for the simulation and allows
the user to start simulators. It provides a :class:`ModelFactory` (and
a :class:`ModelMock`) via which the user can instantiate model instances
(*entities*). The function :func:`run()` finally starts the simulation.

"""
from collections import defaultdict
import itertools

import networkx

from mosaik import simmanager
from mosaik import simulator
from mosaik import util
from mosaik.exceptions import ScenarioError


class Entity:
    """An entity represents an instance of a simulation model within mosaik."""
    __slots__ = ['sid', 'eid', 'type', 'rel', 'sim']

    def __init__(self, sid, eid, type, rel, sim):
        self.sid = sid
        """The ID of the simulator this entity belongs to."""

        self.eid = eid
        """The entity's ID."""

        self.type = type
        """The entity's type (or class)."""

        self.rel = rel
        """A list of related entities (their IDs)"""

        self.sim = sim
        """The :class:`~mosaik.simmanager.SimProxy` containing the entity."""

    def __str__(self):
        return '%s(%s)' % (self.__class__.__name__, ', '.join([
            self.sid, self.eid, self.type]))

    def __repr__(self):
        return '%s(%s)' % (self.__class__.__name__, ', '.join([
            self.sid, self.eid, self.type, repr(self.rel), repr(self.sim)]))


class Environment:
    """The environment holds all data required to specify and run the scenario.

    It provides a method to start a simulator process (:meth:`start()`) and
    manages the simulator instances.

    You have to provide a *sim_config* which tells the environment which
    simulators are available and how to start them. See
    :func:`mosaik.simmanager.start()` for more details.

    If *execution_graph* is set to ``True``, an execution graph will be created
    during the simulation. This may be useful for debugging and testing. Note,
    that this increases the memory consumption and simulation time.

    """
    def __init__(self, sim_config, execution_graph=False):
        self.sim_config = sim_config
        """The config dictionary that tells mosaik how to start a simulator."""

        self.sims = {}
        """A dictionary of already started simulators instances."""

        self.simpy_env = None
        """The SimPy :class:`~simpy.core.Environment` used during the
        simulation."""

        self.df_graph = networkx.DiGraph()
        """The directed dataflow graph for this scenario."""

        self._debug = False
        if execution_graph:
            self._debug = True
            self.execution_graph = networkx.DiGraph()

        # Contains ID counters for each simulator type.
        self._sim_ids = defaultdict(itertools.count)
        # List of outputs for each simulator and model:
        # _df_outattr[sim_id][entity_id] = [attr_1, attr2, ...]
        self._df_outattr = defaultdict(lambda: defaultdict(list))
        # Cache for simulation results
        self._df_cache = util.OrderedDefaultdict(dict)

    def start(self, sim_name, **sim_params):
        """Start the simulator named *sim_name* and return a
        :class:`ModelFactory` for it.

        """
        counter = self._sim_ids[sim_name]
        sim_id = '%s-%s' % (sim_name, next(counter))
        sim = simmanager.start(sim_name, self.sim_config, sim_id, sim_params)
        self.sims[sim_id] = sim
        self.df_graph.add_node(sim_id)
        return ModelFactory(sim)

    def connect(self, src, dest, *attr_pairs):
        """Connect the *src* entity to *dest* entity.

        Establish a dataflow for each ``(src_attr, dest_attr)`` tuple in
        *attr_pairs*.

        Raise a :exc:`~mosaik.exceptions.ScenarioError` if both entities share
        the same simulator instance, if at least one (src. or dest.) attribute
        in *attr_pairs* does not exist, or if the connection would introduce
        a cycle in the dataflow (e.g., A → B → C → A).

        """
        if src.sid == dest.sid:
            raise ScenarioError('Cannot connect entities sharing the same '
                                'simulator.')

        missing_attrs = self._check_attributes(src, dest, attr_pairs)
        if missing_attrs:
            raise ScenarioError('At least on attribute does not exist: %s' %
                                ', '.join('%s.%s' % x for x in missing_attrs))

        # Add edge and check for cycles and the dataflow graph.
        self.df_graph.add_edge(src.sid, dest.sid)
        if not networkx.is_directed_acyclic_graph(self.df_graph):
            self.df_graph.remove_edge(src.sid, dest.sid)
            raise ScenarioError('Connection from "%s" to "%s" introduces '
                                'cyclic dependencies.' % (src.sid, dest.sid))

        dfs = self.df_graph[src.sid][dest.sid].setdefault('dataflows', [])
        dfs.append((src.eid, dest.eid, attr_pairs))

        # Cache the attribute names which we need output data for after a
        # simulation step to reduce the number of df graph queries.
        self._df_outattr[src.sid][src.eid].extend(a[0] for a in attr_pairs)

    def run(self, until):
        """Start the simulation until the simulation time *until* is reached.

        Return the current simulation time (>= *until*).

        This method should only be called once!

        """
        if self._debug:
            import mosaik._debug as dbg
            dbg.enable()
        try:
            res = simulator.run(self, until)
            self._shutdown()
            return res
        finally:
            if self._debug:
                dbg.disable()

    def _check_attributes(self, src, dest, attr_pairs):
        """Check if *src* and *dest* have the attributes in *attr_pairs*.

        Raise a :exc:`ScenarioError` if an attribute does not exist.

        """
        attr_errors = []
        for attr_pair in attr_pairs:
            for entity, attr in zip([src, dest], attr_pair):
                if attr not in entity.sim.meta['models'][entity.type]['attrs']:
                    attr_errors.append((entity, attr))
        return attr_errors

    def _shutdown(self):
        """Shut-down all simulators."""
        for sim in self.sims.values():
            sim.stop()


class ModelFactory:
    """This is a facade for a simulator *sim* that allows the user to create
    new model instances (entities) within that simulator.

    For every model that a simulator publicly exposes, the ``ModelFactory``
    provides a :class:`ModelMock` attribute that actually creates the entities.

    If you access an attribute that is not a model or if the model is not
    marked as *public*, an :exc:`ScenarioError` is raised.

    """
    def __init__(self, sim):
        self._sim = sim
        self._meta = sim.meta
        self._model_cache = {}

    def __getattr__(self, name):
        if name not in self._meta['models']:
            raise ScenarioError('Model factory for "%s" has no model "%s".' %
                                (self._sim.sid, name))
        if not self._meta['models'][name]['public']:
            raise ScenarioError('Model "%s" is not public.' % name)

        if name not in self._model_cache:
            self._model_cache[name] = ModelMock(name, self._sim)

        return self._model_cache[name]


class ModelMock:
    """Instances of this class are exposed as attributes of
    :class:`ModelFactory` and allow the instantiation of simulator models.

    You can *call* an instance of this class to create exactly one entiy:
    ``sim.ModelName(x=23)``. Alternatively, you can use the :meth:`create()`
    method to create multiple entities with the same set of parameters at once:
    ``sim.ModelName.create(3, x=23)``.

    """
    def __init__(self, name, sim):
        self._name = name
        self._sim = sim
        self._sim_id = sim.sid

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
        entities = self._sim.create(num, self._name, model_params)
        sim_id = self._sim_id
        return [Entity(sim_id, e['eid'], e['type'], e['rel'], self._sim)
                for e in entities]
