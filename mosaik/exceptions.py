"""
This module provides mosaik specific exception types.
"""

from typing import Any, List, Tuple

from mosaik_api_v3 import SimId


class ScenarioError(Exception):
    """
    This exception is raised if something fails during the creation of
    a scenario.
    """


class SimulationError(Exception):
    """
    This exception is raised if a simulator cannot be started or if
    a problem arises during the execution of a simulation.
    """

    def __init__(self, msg: str, exc: Any = None):
        arg = ""
        if exc:
            orig = str(exc)
            if orig.endswith("."):
                orig = orig[:-1]
            arg += "%s: " % orig
        arg += msg
        super().__init__(arg)


class NonSerializableOutputsError(SimulationError):
    """This exception is raised if a simulator started via ``"python"``
    returns output that cannot be serialized to JSON but you try to
    transmit this data to a simulator started via ``"cmd"`` or
    ``"connect"``.

    There are two possible resolutions:
    - Contact the simulator author to have them change their output
      datatypes to standard Python types that can be serialized.
    - Start the destination simulator via ``"python"`` as well. This
      resolution is mostly sensible if the two simulators are tightly
      coupled and are supposed to exchange non-primitive objects
      directly.
    """

    dest: SimId
    errors: List[Tuple[str, str, str, TypeError]]

    def __init__(self, dest: SimId):
        self.dest = dest
        self.errors = []

    def add_error(self, dest_eid: str, dest_attr: str, src_id: str, error: TypeError):
        self.errors.append((dest_eid, dest_attr, src_id, error))

    def __bool__(self):
        return bool(self.errors)

    def __str__(self) -> str:
        return (
            f"Errors while trying to JSON-serialize inputs for {self.dest}:\n"
            + "\n".join(
                f"- serializing output from {src} for {dest_eid}.{dest_attr}: "
                f"{str(error)}"
                for dest_eid, dest_attr, src, error in self.errors
            )
            + "\nThis is likely a problem in the source simulator(s)."
        )


class SimulatorError(Exception):
    """This is the supertype for exceptions raised if a simulator does
    not behave correctly.

    If you encounter one of these exceptions as a scenario author, you
    should usually contact the auther of the simulator in question to
    resolve the issue.
    """

    simulator: str

    def __init__(self, simulator: str, *args: Any) -> None:
        self.simulator = simulator
        super().__init__(*args)


class DuplicateEntityIdError(SimulatorError):
    """This exception is raised if a simulator returns multiple entities
    with the same entity ID."""

    entity_id: str

    def __init__(self, simulator: str, entity_id: str, *args: Any) -> None:
        self.entity_id = entity_id
        super().__init__(simulator, *args)

    def __str__(self) -> str:
        return (
            f"Simulator {self.simulator} returned multiple entities "
            f"with entity ID '{self.entity_id}'."
        )
