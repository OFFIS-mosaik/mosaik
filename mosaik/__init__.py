"""
This module provides convenient access to all classes and functions required
to create scenarios and run simulations.

Currently, this is only :class:`mosaik.scenario.World`.

"""
from importlib import metadata

from mosaik.scenario import SimConfig, World

__version__ = metadata.version("mosaik")
__all__ = ['SimConfig', 'World']
