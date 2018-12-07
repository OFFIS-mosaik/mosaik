"""
This module provides convenient access to all classes and functions required
to create scenarios and run simulations.

Currently, this is only :class:`mosaik.scenario.World`.

"""
from mosaik.scenario import World
from mosaik import _version

__version__ = _version.VERSION
__all__ = ['World']
