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
        arg = ''
        if exc:
            orig = str(exc)
            if orig.endswith('.'):
                orig = orig[:-1]
            arg += '%s: ' % orig
        arg += msg
        super().__init__(arg)


class NonSerializableOutputsError(SimulationError):
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
                f"- serializing output from {src} for {dest_eid}.{dest_attr}: {str(error)}"
                for dest_eid, dest_attr, src, error in self.errors
            )
            + "\nThis is likely a problem in the source simulator(s)."
        )
