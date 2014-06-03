"""
This module contains some utility functions and classes.

"""
import collections
import sys

from simpy.io.network import RemoteException


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


def sync_process(generator, world, err_msg=None, ignore_errors=False):
    """Synchronously execute a SimPy process defined by the generator object
    *generator*.

    A *world* instance is required to run the event loop.

    You can optionally provide a *err_msg* that will be printed when the
    remote site unexpectedly closes its connection.

    If *ignore_errors* is set to ``True``, no errors will be printed.

    """
    try:
        return world.env.run(until=world.env.process(generator))
    except ConnectionResetError:
        if ignore_errors:
            # Avoid endless recursions when called from "world.shutdown()"
            return
        print_exception_and_exit(err_msg, world.shutdown)
    except RemoteException as e:
        if ignore_errors:
            # Avoid endless recursions when called from "world.shutdown()"
            return
        print_exception_and_exit(e, world.shutdown)


def print_exception_and_exit(error, callback=None):
    """Print the error defined by the string or exception *error*, optionally
    calling *callback*."""
    if type(error) is RemoteException:
        print('RemoteException:')
        print(error.remote_traceback)
        print('————————————————')
    else:
        print('ERROR:', error)

    if callback:
        callback()

    print('Mosaik terminating')
    sys.exit(1)
