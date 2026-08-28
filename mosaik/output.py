"""While output is handled by normal simulators in mosaik, it is still
somewhat of a special case. The :class:`OutputSim` class is a wrapper
for the :class:`~mosaik.async_scenario.AsyncModelFactory` (i.e. the
class that normally represents simulators in a mosaik scenario). It
standardizes connection patterns for output simulators.

Using this model will simplify swapping your output simulator because
you only need to create your ``outputs`` object with a different
simulator.

In this documentation, **domain model** and **domain entity** refer to
(mosaik) models and entities from your actual simulation, whereas
**storage models** and **storage entities** are models and entities
used by the output simulator.


How to recognize OutputSim-ready simulators
-------------------------------------------

Not all output simulators can be used with this wrapper yet. For
simulators developed by us, check whether they mention being
"OutputSim-ready" in their README.


How to use as a scenario author
-------------------------------

To use this adapter, your scenario must use mosaik's
:class:`~mosaik.async_scenario.AsyncWorld`.

At to the start of your scenario, create the instance of your output
simulator and wrap it in :class:`OutputSim` like so::

    outputs = OutputSim(await world.start(...))

where ``...`` is replaced by the appropriate parameters to start your
output simulator.

Then, for all entities that should store outputs, call
:meth:`~OutputSim.collect_from` like so::

    await outputs.collect_from(entity, *attrs)

where ``attrs`` are the entities you want to be stored.

If you leave ``attrs`` blank, all output attributes are stored.
(This only works if the simulator is modern enough to list outputs
separately in its META.)

To collect output from multiple entities at once, you may also use
:meth:`~OutputSim.collect_from_all`.


Special cases
^^^^^^^^^^^^^

By default, :class:`OutputSim` expects that an output simulator either
provides a single model used for all outputs, or separate output models
for all domain models, where the output and domain models share the same
name. If this is not the case, for example because the output simulator
creates its models based on the tables in an SQL database but the names
do not line up perfectly, you can pass a :type:`EntityMapper` to the
constructor of :class:`OutputSim`.


How to make your own output simulator OutputSim-ready
-----------------------------------------------------

:class:`OutputSim` expects that a single instance of the output
simulator can handle the entire simulation's outputs. It works with
output simulators set up in one of two ways:

1. The output simulator provides a single model to be used for all
   output entities. In this case, this model usually will have
   ``"any_inputs"`` set to ``True`` in its ``META``.
2. The output simulator has a separate model for each type of data.
   (For example, because different models write their outputs to
   different tables in a database.) In this case, the input attributes
   are often fixed by the model.

In either case, the :class:`OutputSim` will create an entity in the
output simulator for each domain entity connected to it. In ``create``,
the output simulator will be passed the model and full entity ID of the
domain entity as ``domain_model`` and ``full_id``, respectively.

It is up to the output simulator author to decide how to store the data.
"""

from collections.abc import Callable, Iterable

from mosaik_api_v3.types import Attr, ModelName

from mosaik.async_scenario import AsyncModelFactory, Entity


def _extract_singleton[K, V](d: dict[K, V]) -> tuple[K, V] | None:
    res = None
    for pair in d.items():
        if res is not None:
            return None
        else:
            res = pair
    return res


type EntityMapper = Callable[[Entity], ModelName]
"""A function describing how to turn entities of your domain into
storage entities of the output simulator. If your simulator only has one
model, or if the names of the storage models line up perfectly with the
names of the domain models, you can keep the default value. Otherwise,
this function should map a (domain) entity to a model name of the output
simulator. An entity of that storage model will be created to store that
domain entity's output.
"""


class OutputSim:
    """A wrapper class for a
    :class:`~mosaik.async_scenario.AsyncModelFactory` to make the
    collecting of output data in a mosaik simulation easier.
    """

    _sim: AsyncModelFactory
    _entity_mapper: EntityMapper
    _storage_entities: dict[Entity, Entity]

    def __init__(
        self,
        sim: AsyncModelFactory,
        *,
        entity_mapper: EntityMapper | None = None,
    ):
        self._sim = sim

        if not entity_mapper:
            if pair := _extract_singleton(self._sim._proxy.meta["models"]):
                self._entity_mapper = lambda _entity: pair[0]
            else:
                self._entity_mapper = lambda entity: entity.model
        else:
            self._entity_mapper = entity_mapper

        self._storage_entities = {}

    async def get_storage_entity(self, entity: Entity) -> Entity:
        """Get the storage entity for the given ``entity``.

        The first time this is called for a given ``entity``, a new
        storage entity will be created for it, by first using the
        :type:`EntityMapper` to determine the right model and then
        creating an entity of that model in the output simulator.
        On subsequent calls for the same domain entity, the same
        storage entity will be returned.
        """
        if storage_entity := self._storage_entities.get(entity):
            return storage_entity

        storage_model = self._entity_mapper(entity)
        storage_entity = await self._sim.models[storage_model](
            domain_model=entity.model, full_id=entity.full_id
        )
        self._storage_entities[entity] = storage_entity
        return storage_entity

    async def collect_from(self, entity: Entity, *attrs: Attr | tuple[Attr, Attr]):
        """Collect the data from ``entity`` in the output simulator.

        The attributes to collect can be specified as in
        :meth:`~mosaik.async_scenario.AsyncWorld.connect`; if no attrs
        are specfied this way, all of the entity's output attributes
        are stored.
        """
        if not attrs:
            attrs = tuple(entity.model_mock.output_attrs)

        self._sim._world.connect(entity, await self.get_storage_entity(entity), *attrs)

    async def collect_from_all(
        self, entities: Iterable[Entity], *attrs: Attr | tuple[Attr, Attr]
    ):
        """Collect data from all entities in ``entities``.

        This simply calls :meth:`collect_from` for each of those
        entities.
        """
        for entity in entities:
            await self.collect_from(entity, *attrs)
