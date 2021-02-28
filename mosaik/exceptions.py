"""
This module provides mosaik specific exception types.
"""


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

    def __init__(self, msg, exc=None):
        arg = ''
        if exc:
            orig = str(exc)
            if orig.endswith('.'):
                orig = orig[:-1]
            arg += '%s: ' % orig
        arg += msg
        super().__init__(arg)


class WakeUpException(Exception):
    """
    This exception is raised if a simulator is woken up by a successor
    which has terminated.
    """

class NoStepException(Exception):
    """
    This exception is raised if none of the simulators has a next step.
    """
