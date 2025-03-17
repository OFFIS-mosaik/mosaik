"""
This module provides convenient access to all classes and functions
required to create scenarios and run simulations.
"""

from loguru import logger

from mosaik._version import version

# Saying "import X as X" (with X repeated) is the standard way of
# marking to linters and type checkers that something is re-exported.
from mosaik.async_scenario import AsyncWorld as AsyncWorld
from mosaik.scenario import SimConfig as SimConfig
from mosaik.scenario import World as World

__all__ = ["World", "AsyncWorld"]
__version__ = version

logger.disable(__name__)
