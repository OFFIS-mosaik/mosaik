"""
This module provides the interface for users to create simulation scenarios for
mosaik.

The :class:`World` holds all necessary data for the simulation and allows the
user to start simulators. It provides a :class:`ModelFactory` (and
a :class:`ModelMock`) via which the user can instantiate model instances
(*entities*). The method :meth:`World.run()` finally starts the simulation.

"""
from collections import defaultdict
import itertools
import sys

import networkx

from mosaik import simmanager
from mosaik import simulator
from mosaik import util
from mosaik.exceptions import ScenarioError


backend = simmanager.backend
base_config = {
    'addr': ('127.0.0.1', 5555),
    'start_timeout': 2,  # seconds
    'stop_timeout': 2,  # seconds
}


class Entity:
    """An entity represents an instance of a simulation model within mosaik."""
    __slots__ = ['sid', 'eid', 'type', 'children', 'sim']

    def __init__(self, sid, eid, type, children, sim):
        self.sid = sid
        """The ID of the simulator this entity belongs to."""

        self.eid = eid
        """The entity's ID."""

        self.type = type
        """The entity's type (or class)."""

        self.children = children if children is not None else set()
        """An entity set containing subordinate entities."""

        self.sim = sim
        """The :class:`~mosaik.simmanager.SimProxy` containing the entity."""

    @property
    def full_id(self):
        """Full, globally unique entity id ``sid/eid``."""
        return '%s/%s' % (self.sid, self.eid)

    def __str__(self):
        return '%s(%s)' % (self.__class__.__name__, ', '.join([
            self.sid, self.eid, self.type]))

    def __repr__(self):
        return '%s(%s)' % (self.__class__.__name__, ', '.join([
            self.sid, self.eid, self.type, repr(self.children),
            repr(self.sim)]))


class World:
    """The world holds all data required to specify and run the scenario.

    It provides a method to start a simulator process (:meth:`start()`) and
    manages the simulator instances.

    You have to provide a *sim_config* which tells the world which simulators
    are available and how to start them. See :func:`mosaik.simmanager.start()`
    for more details.

    *mosaik_config* can be a dict or list of key-value pairs to set addional
    parameters overriding the defaults::

        {
            'addr': ('127.0.0.1', 5555),
            'start_timeout': 2,  # seconds
            'stop_timeout': 2,   # seconds
        }

    Here, *addr* is the network address that mosaik will bind its socket to.
    *start_timeout* and *stop_timeout* specifiy a timeout (in seconds) for
    starting/stopping external simulator processes.

    If *execution_graph* is set to ``True``, an execution graph will be created
    during the simulation. This may be useful for debugging and testing. Note,
    that this increases the memory consumption and simulation time.

    """
    def __init__(self, sim_config, mosaik_config=None, execution_graph=False):
        self.sim_config = sim_config
        """The config dictionary that tells mosaik how to start a simulator."""

        self.config = dict(base_config)
        """The config dictionary for general mosaik settings."""
        if mosaik_config:
            self.config.update(mosaik_config)

        self.sims = {}
        """A dictionary of already started simulators instances."""

        self.env = backend.Environment()
        """The SimPy.io networking :class:`~simpy.io.select.Environment`."""

        self.srv_sock = backend.TCPSocket.server(self.env, self.config['addr'])
        """Mosaik's server socket."""

        self.df_graph = networkx.DiGraph()
        """The directed dataflow graph for this scenario."""

        self.entity_graph = networkx.Graph()
        """The graph of related entities. Nodes are ``(sid, eid)`` tuples.
        Each note has an attribute *entity* with an :class:`Entity`."""

        self.sim_progress = 0
        """Progress of the current simulation."""

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
        print('Starting "%s" as "%s" ...' % (sim_name, sim_id))
        sim = simmanager.start(self, sim_name, sim_id, sim_params)
        self.sims[sim_id] = sim
        self.df_graph.add_node(sim_id)
        return ModelFactory(self, sim)

    def connect(self, src, dest, *attr_pairs, async_requests=False):
        """Connect the *src* entity to *dest* entity.

        Establish a dataflow for each ``(src_attr, dest_attr)`` tuple in
        *attr_pairs*. If *src_attr* and *dest_attr* have the same name, you
        you can optionally only pass one of them as a single string.

        Raise a :exc:`~mosaik.exceptions.ScenarioError` if both entities share
        the same simulator instance, if at least one (src. or dest.) attribute
        in *attr_pairs* does not exist, or if the connection would introduce
        a cycle in the dataflow (e.g., A → B → C → A).

        If the *dest* simulator may make asyncronous requests to mosaik to
        query data from *src* (or set data to it), *async_requests* should be
        set to ``True`` so that the *src* simulator stays in sync with *dest*.

        """
        if src.sid == dest.sid:
            raise ScenarioError('Cannot connect entities sharing the same '
                                'simulator.')

        # Expand single attributes "attr" to ("attr", "attr") tuples:
        attr_pairs = tuple((a, a) if type(a) is str else a for a in attr_pairs)

        missing_attrs = self._check_attributes(src, dest, attr_pairs)
        if missing_attrs:
            raise ScenarioError('At least one attribute does not exist: %s' %
                                ', '.join('%s.%s' % x for x in missing_attrs))

        # Add edge and check for cycles and the dataflow graph.
        self.df_graph.add_edge(src.sid, dest.sid,
                               async_requests=async_requests)
        if not networkx.is_directed_acyclic_graph(self.df_graph):
            self.df_graph.remove_edge(src.sid, dest.sid)
            raise ScenarioError('Connection from "%s" to "%s" introduces '
                                'cyclic dependencies.' % (src.sid, dest.sid))

        dfs = self.df_graph[src.sid][dest.sid].setdefault('dataflows', [])
        dfs.append((src.eid, dest.eid, attr_pairs))

        # Add relation in entity_graph
        self.entity_graph.add_edge('%s/%s' % (src.sid, src.eid),
                                   '%s/%s' % (dest.sid, dest.eid))

        # Cache the attribute names which we need output data for after a
        # simulation step to reduce the number of df graph queries.
        outattr = [a[0] for a in attr_pairs]
        if outattr:
            self._df_outattr[src.sid][src.eid].extend(outattr)

    def get_data(self, entity_set, *attributes):
        """Get and return the values of all *attributes* for each entity of an
        *entity_set*.

        The return value is a dict mapping the entities of *entity_set* to
        dicts containing the values of each attribute in *attributes*::

            {
                Entity(...): {
                    'attr_1': 'val_1',
                    'attr_2': 'val_2',
                    ...
                },
                ...
            }

        """
        outputs_by_sim = defaultdict(dict)
        for entity in entity_set:
            outputs_by_sim[entity.sid][entity.eid] = attributes

        def request_data():
            requests = {self.sims[sid].get_data(outputs): sid
                        for sid, outputs in outputs_by_sim.items()}
            results = yield self.env.all_of(requests)

            results_by_sim = {}
            for request, value in results.items():
                sid = requests[request]
                results_by_sim[sid] = value

            return results_by_sim

        results_by_sim = util.sync_process(request_data(), self,
                                           'A simulator closed its connection '
                                           'during "get_data()".')
        results = {}
        for entity in entity_set:
            results[entity] = results_by_sim[entity.sid][entity.eid]

        return results

    def run(self, until):
        """Start the simulation until the simulation time *until* is reached.

        Return the current simulation time (>= *until*).

        This method should only be called once!

        """
        print('Starting simulation.')
        if self._debug:
            import mosaik._debug as dbg
            dbg.enable()
        try:
            util.sync_process(simulator.run(self, until), self,
                              'A simulator closed its connection.')
            print('Simulation finished successfully.')
        except KeyboardInterrupt:
            print('Simulation canceled. Terminating ...')
            sys.exit(1)
        finally:
            self.shutdown()
            if self._debug:
                dbg.disable()

    def shutdown(self):
        """Shut-down all simulators and close the server socket."""
        for sim in self.sims.values():
            util.sync_process(sim.stop(), self, ignore_errors=True)
        self.srv_sock.close()

    def _check_attributes(self, src, dest, attr_pairs):
        """Check if *src* and *dest* have the attributes in *attr_pairs*.

        Raise a :exc:`~mosaik.exceptions.ScenarioError` if an attribute does
        not exist.

        """
        attr_errors = []
        for attr_pair in attr_pairs:
            for entity, attr in zip([src, dest], attr_pair):
                if attr not in entity.sim.meta['models'][entity.type]['attrs']:
                    attr_errors.append((entity, attr))
        return attr_errors


class ModelFactory:
    """This is a facade for a simulator *sim* that allows the user to create
    new model instances (entities) within that simulator.

    For every model that a simulator publicly exposes, the ``ModelFactory``
    provides a :class:`ModelMock` attribute that actually creates the entities.

    If you access an attribute that is not a model or if the model is not
    marked as *public*, an :exc:`~mosaik.exceptions.ScenarioError` is raised.

    """
    def __init__(self, world, sim):
        self.meta = sim.meta
        self._world = world
        self._env = world.env
        self._sim = sim
        self._model_cache = {}

    def __getattr__(self, name):
        if name not in self.meta['models']:
            raise ScenarioError('Model factory for "%s" has no model "%s".' %
                                (self._sim.sid, name))
        if not self.meta['models'][name]['public']:
            raise ScenarioError('Model "%s" is not public.' % name)

        if name not in self._model_cache:
            self._model_cache[name] = ModelMock(self._world, name, self._sim)

        return self._model_cache[name]


class ModelMock:
    """Instances of this class are exposed as attributes of
    :class:`ModelFactory` and allow the instantiation of simulator models.

    You can *call* an instance of this class to create exactly one entiy:
    ``sim.ModelName(x=23)``. Alternatively, you can use the :meth:`create()`
    method to create multiple entities with the same set of parameters at once:
    ``sim.ModelName.create(3, x=23)``.

    """
    def __init__(self, world, name, sim):
        self._world = world
        self._env = world.env
        self._name = name
        self._sim = sim
        self._sim_id = sim.sid
        self._params = sim.meta['models'][name]['params']

    def __call__(self, **model_params):
        """Call :meth:`create()` to instantiate one model."""
        self._check_params(**model_params)
        return self.create(1, **model_params)[0]

    def create(self, num, **model_params):
        """Create *num* entities with the specified *model_params* and return
        a list with the entity dicts.

        The returned list of entities is the same as returned by
        :meth:`mosaik_api.Simulator.create()`, but the simulator is prepended
        to every entity ID to make them globally unique.

        """
        self._check_params(**model_params)

        # We have to start a SimPy process to make the "create()" call
        # behave like it was synchronous.
        def create_proc():
            entities = yield self._sim.create(num, self._name, **model_params)
            return entities

        entities = util.sync_process(create_proc(), self._world,
                                     '"%s" closed its connection during the '
                                     'creation of %s instances of "%s".' % (
                                         self._sim_id, num, self._name))
        assert len(entities) == num, (
            '%d entities were requested but %d were created.' %
            (num, len(entities)))

        return self._make_entities(entities, assert_type=self._name)

    def _check_params(self, **model_params):
        expected_params = list(self._params)
        for param in model_params:
            if param not in expected_params:
                raise TypeError("create() got an unexpected keyword argument "
                                "'%s'" % param)
            expected_params.remove(param)

    def _make_entities(self, entity_dicts, assert_type=None):
        """Recursively create lists of :class:`Entity` instance from a list
        of *entity_dicts*."""
        sim_id = self._sim_id
        entity_graph = self._world.entity_graph

        entity_set = []
        for e in entity_dicts:
            self._assert_model_type(assert_type, e)

            children = e.get('children', [])
            if children:
                children = self._make_entities(children)
            entity = Entity(sim_id, e['eid'], e['type'], children,
                            self._sim)

            entity_set.append(entity)
            entity_graph.add_node('%s/%s' % (sim_id, e['eid']), type=e['type'])
            for rel in e['rel']:
                entity_graph.add_edge('%s/%s' % (sim_id, e['eid']),
                                      '%s/%s' % (sim_id, rel))

        return entity_set

    def _assert_model_type(self, assert_type, e):
        """Assert that entity *e* has either type *assert_type* if is not none
        or else any valid type."""
        if assert_type is not None:
            assert e['type'] == assert_type, (
                'Entity "%s" has the wrong type: "%s"; "%s" required.' %
                (e['eid'], e['type'], assert_type))
        else:
            assert e['type'] in self._sim.meta['models'], (
                'Type "%s" of entity "%s" not found in sim\'s meta data.' %
                (e['type'], e['eid']))
