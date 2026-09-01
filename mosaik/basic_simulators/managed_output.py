from __future__ import annotations

from copy import deepcopy
from typing import Any

import mosaik_api_v3
from mosaik_api_v3.types import (
    CreateResult,
    InputData,
    Meta,
    ModelName,
    OutputData,
    OutputRequest,
    SimId,
    Time,
)

import mosaik
import mosaik.exceptions

META: Meta = {
    "api_version": "3.0",
    "type": "event-based",
    "extra_methods": ["get_for_full_id", "get_all"],
    "models": {
        "Dict": {
            "public": True,
            "any_inputs": True,
            "params": [
                "storage_type",
                "storage_id",
                "storage_ids",
                "extra_info",
                "extra_infos",
            ],
            "attrs": [],
        },
    },
}


def unify_one_or_more[T](single: T | None, multiple: list[T] | None) -> list[T]:
    """Assert that exactly one of ``single`` and ``multiple`` is not
    ``None`` and return it; with ``single`` turned into a one-element
    list.

    This function is intended to make writing the ``create`` method
    easier.
    """
    if single is not None:
        assert multiple is None
        return [single]
    else:
        assert multiple is not None
        return multiple


class Simulator(mosaik_api_v3.Simulator):
    """This simulator takes the input it is given and writes it into a
    Python dictionary where the keys are the timestamps of the input and
    the values are the inputs values.
    """

    domain_to_storage: dict[str, str]
    entities: dict[str, dict[Time, Any]]

    def __init__(self):
        super().__init__(META)
        self.entities = {}  # Maps EIDs to model instances/entities
        self.domain_to_storage = {}

    def init(self, sid: SimId, time_resolution: float = 1):
        return self.meta

    def create(
        self,
        num: int,
        model: ModelName,
        storage_type: str,
        storage_id: str | None = None,
        storage_ids: list[str] | None = None,
        extra_info: Any = None,
        extra_infos: Any = None,
    ) -> list[CreateResult]:
        storage_ids = unify_one_or_more(storage_id, storage_ids)
        assert len(storage_ids) == num

        entities: list[CreateResult] = []
        for stid in storage_ids:
            model_instance = {}
            eid = f"{model}-{len(self.entities)}"
            self.domain_to_storage[stid] = eid
            self.entities[eid] = model_instance
            entities.append({"eid": eid, "type": model})
        return entities

    def step(self, time: Time, inputs: InputData, max_advance: Time):
        for receiver, input in inputs.items():
            self.entities[receiver][time] = _remove_sources(input)

    def get_data(self, outputs: OutputRequest) -> OutputData:
        raise mosaik.exceptions.ScenarioError(
            "This function is not supposed to be used in this simulator. "
            "Use this simulator for input data only."
        )

    def get_for_full_id(self, full_id: str) -> dict[Time, Any]:
        """
        Returns the dict of the simulator entity specified by the
        ``eid``.

        :param eid: The entity id of the selected entity.

        :return: The dict of the entity.
        """
        return self.entities[self.domain_to_storage[full_id]]

    def get_all(self) -> dict[str, dict[Time, Any]]:
        return {
            full_id: self.entities[eid]
            for full_id, eid in self.domain_to_storage.items()
        }


def _remove_sources(entity_inputs: dict[str, dict[str, Any]]) -> dict[str, Any]:
    res: dict[str, Any] = {}
    for attr, values in entity_inputs.items():
        for value in values.values():
            res[attr] = deepcopy(value)
    return res
