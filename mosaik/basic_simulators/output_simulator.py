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
    "extra_methods": ["get_dict"],
    "models": {
        "Dict": {
            "public": True,
            "any_inputs": True,
            "params": [],
            "attrs": [],
        },
    },
}


class OutputSimulator(mosaik_api_v3.Simulator):
    """
    This simulator takes the input it is given and writes it into a
    Python dictionary where the keys are the timestamps of the input and
    the values are the inputs values.

    The dictionary can be retrieved using the :meth:`get_dict` method.
    """

    entities: dict[str, dict[Time, Any]]

    def __init__(self):
        super().__init__(META)
        self.entities = {}  # Maps EIDs to model instances/entities

    def init(self, sid: SimId, time_resolution: float = 1):
        return self.meta

    def create(
        self, num: int, model: ModelName, **model_params: Any
    ) -> list[CreateResult]:
        next_eid = len(self.entities)
        entities: list[CreateResult] = []
        for i in range(next_eid, next_eid + num):
            model_instance = {}
            eid = f"{model}-{i}"
            self.entities[eid] = model_instance
            entities.append({"eid": eid, "type": model})
        return entities

    def step(self, time: Time, inputs: InputData, max_advance: Time):
        for receiver, input in inputs.items():
            self.entities[receiver][time] = deepcopy(input)

    def get_data(self, outputs: OutputRequest) -> OutputData:
        raise mosaik.exceptions.ScenarioError(
            "This function is not supposed to be used in this simulator. "
            "Use this simulator for input data only."
        )

    def get_dict(self, eid: str) -> dict[Time, Any]:
        """
        Returns the dict of the simulator entity specified by the
        ``eid``.

        :param eid: The entity id of the selected entity.

        :return: The dict of the entity.
        """
        return self.entities[eid]
