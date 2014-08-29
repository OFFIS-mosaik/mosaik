"""
This module contains some utility functions and classes.

"""
import collections
import sys

from simpy.io.network import RemoteException

from mosaik.exceptions import SimulationError


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


def sync_process(generator, world, *, ignore_errors=False):
    """Synchronously execute a SimPy process defined by the generator object
    *generator*.

    A *world* instance is required to run the event loop.

    You can optionally provide a *err_msg* that will be printed when the
    remote site unexpectedly closes its connection.

    If *ignore_errors* is set to ``True``, no errors will be printed.

    """
    try:
        return world.env.run(until=world.env.process(generator))
    except (ConnectionError, RemoteException, SimulationError) as exc:
        if ignore_errors:
            # Avoid endless recursions when called from "world.shutdown()"
            return

        if type(exc) is RemoteException:
            print('RemoteException:')
            print(exc.remote_traceback)
            print('————————————————')
        else:
            print('ERROR: %s' % exc)

        print('Mosaik terminating')
        world.shutdown()
        sys.exit(1)
