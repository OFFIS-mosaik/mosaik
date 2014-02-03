"""
This module provides mosaik specific exception types.

"""


class ScenarioError(Exception):
    """This exception is raised if something fails during the creationg of
    a scenario.

    """


class SimulationError(Exception):
    """This exception is raised if a simulator cannot be started or if
    a problem arises during the execution of a simulation.

    """
