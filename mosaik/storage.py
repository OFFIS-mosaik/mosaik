"""While output is handled by normal simulators in mosaik, it is still
somewhat of a special case. The :class:`StorageManager` class is a
wrapper for the :class:`~mosaik.async_scenario.AsyncModelFactory` (i.e.
the class that represents simulators in a mosaik scenario). It
standardizes connection patterns for output simulators.

Using this manager will simplify swapping your output simulator because
you only need to create your ``outputs`` object with a different
simulator.

In this documentation, **domain model** and **domain entity** refer to
(mosaik) models and entities from your actual simulation, whereas
**storage models** and **storage entities** are models and entities
used by the output simulator.


How to recognize StorageManager-ready simulators
------------------------------------------------

Not all output simulators can be used with this wrapper yet. For
simulators developed by us, check whether they mention being
"StorageManager-ready" in their README.


How to use as a scenario author
-------------------------------

To use this adapter, your scenario must use mosaik's
:class:`~mosaik.async_scenario.AsyncWorld`.

At to the start of your scenario, create the instance of your output
simulator and wrap it in :class:`OutputSim` like so::

    outputs = StorageManager(await world.start(...))

where ``...`` is replaced by the appropriate parameters to start your
output simulator.

Then, for all entities that should store outputs, call
:meth:`~StorageManager.collect_from` like so::

    await outputs.collect_from(entity, *attrs)

where ``attrs`` are the entities you want to be stored.

If you leave ``attrs`` blank, all output attributes are stored.
(This only works if the simulator is modern enough to list outputs
separately in its META.)

To collect output from multiple entities at once, you may also use
:meth:`~StorageManager.collect_from_all`.


Special cases
^^^^^^^^^^^^^

By default, :class:`StorageManager` expects that an output simulator
either provides a single model used for all outputs, or separate output
models for all domain models, where the output and domain models share
the same name. If this is not the case, for example because the output
simulator creates its models based on the tables in an SQL database but
the names do not line up perfectly, you can pass a :type:`EntityMapper`
to the constructor of :class:`StorageManager`.


How to make your own output simulator StorageManager-ready
----------------------------------------------------------

:class:`StorageManager` expects that a single instance of the output
simulator can handle the entire simulation's outputs. It works with
output simulators set up in one of two ways:

1. The output simulator provides a single model to be used for all
   output entities. In this case, this model usually will have
   ``"any_inputs"`` set to ``True`` in its ``META``.
2. The output simulator has a separate model for each type of data.
   (For example, because different models write their outputs to
   different tables in a database.) In this case, the input attributes
   are often fixed by the model.

In either case, the :class:`StorageManager` will create an entity in the
output simulator for each domain entity connected to it. In ``create``,
the output simulator will be passed the model and full entity ID of the
domain entity as ``storage_type`` and ``storage_id``, respectively.

It is up to the output simulator author to decide how to store the data.
"""

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any

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


@dataclass
class EntityStorage:
    storage_model: ModelName | None = None
    storage_type: str | None = None
    storage_id: str | None = None
    extra_info: Any | None = None


type EntityMapper = Callable[[Entity], EntityStorage]
"""A function describing how to turn entities of your domain into
storage entities of the output simulator. If your simulator only has one
model, or if the names of the storage models line up perfectly with the
names of the domain models, you can keep the default value. Otherwise,
this function should map a (domain) entity to a model name of the output
simulator. An entity of that storage model will be created to store that
domain entity's output.
"""


class StorageManager:
    """A wrapper class for a
    :class:`~mosaik.async_scenario.AsyncModelFactory` to make the
    collecting of output data in a mosaik simulation easier.
    """

    _sim: AsyncModelFactory
    _entity_mapper: EntityMapper
    _single_model: ModelName | None
    _storage_entities: dict[Entity, Entity]

    def __init__(
        self,
        sim: AsyncModelFactory,
        *,
        entity_mapper: EntityMapper = lambda _: EntityStorage(),
    ):
        self._sim = sim
        if pair := _extract_singleton(self._sim._proxy.meta["models"]):
            self._single_model = pair[0]
        else:
            self._single_model = None

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

        si = self._entity_mapper(entity)
        storage_model = si.storage_model or self._single_model or entity.model
        storage_type = si.storage_type or entity.model
        storage_id = si.storage_id or entity.full_id
        extra_info = si.extra_info or entity.extra_info

        storage_entity = await self._sim.models[storage_model](
            storage_type=storage_type,
            storage_id=storage_id,
            extra_info=extra_info,
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
