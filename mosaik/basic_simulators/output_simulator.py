import mosaik_api_v3
from mosaik_api_v3.types import OutputData, OutputRequest
import mosaik
import mosaik.exceptions
from copy import deepcopy

META = {
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
    This simulator takes the input it is given and writes it into a python dictionary
    where the keys are the timestamps of the input and the values are the inputs values.

    The dictionary can be retrieved using the :meth:`get_dict()` method.
    """

    def __init__(self):
        super().__init__(META)
        self.entities = {}  # Maps EIDs to model instances/entities

    def init(self, sid, time_resolution):
        return self.meta

    def create(self, num, model):
        next_eid = len(self.entities)
        entities = []
        for i in range(next_eid, next_eid + num):
            model_instance = {}
            eid = f"{model}-{i}"
            self.entities[eid] = model_instance
            entities.append({"eid": eid, "type": model})
        return entities

    def step(self, time, inputs, max_advance):
        for entity in self.entities.values():
            entity[time] = deepcopy(inputs)

    def get_data(self, outputs: OutputRequest) -> OutputData:
        raise mosaik.exceptions.ScenarioError(
            "This function is not supposed to be used in this simulator. "
            "Use this simulator for input data only."
        )

    def get_dict(self, eid):
        """
        Returns the dict of the simulator entity specified by the ``eid``.

        :param eid: The entity id of the selected entity.
        :type eid: str

        :return: The dict of the entity.
        """
        return self.entities[eid]
