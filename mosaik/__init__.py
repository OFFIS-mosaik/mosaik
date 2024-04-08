"""
This module provides convenient access to all classes and functions required
to create scenarios and run simulations.

Currently, this is only :class:`mosaik.scenario.World`.

"""
# Saying "import X as X" (with X repeated) is the standard way of
# marking to linters and type checkers that something is re-exported.
from mosaik.scenario import SimConfig as SimConfig
from mosaik.scenario import World as World
from mosaik._version import __version__ as __version__

__all__ = ['World']
