"""
This module contains some utility functions and classes.

"""
import collections


class OrderedDefaultdict(collections.OrderedDict):
    """Mixes :class:`~collections.OrderedDict` with
    :class:`~collections.defaultdict`."""
    def __init__(self, *args, **kwargs):
        if not args:
            self.default_factory = None
        else:
            if not (args[0] is None or hasattr(args[0], '__call__')):
                raise TypeError('first argument must be callable')
            self.default_factory = args[0]
            args = args[1:]
        super().__init__(*args, **kwargs)

    def __missing__(self, key):
        if self.default_factory is None:
            raise KeyError(key)
        self[key] = default = self.default_factory()
        return default
