"""
This module contains utility functions for working with SimPy.
"""

import sys

from simpy.io.network import RemoteException

from mosaik.exceptions import SimulationError


def sync_process(generator, world, *, errback=None, ignore_errors=False):
    """
    Synchronously execute a SimPy process defined by the generator object
    *generator*.

    A *world* instance is required to run the event loop.

    You can optionally provide a *errback* (error callback) which will be
    called with no arguments if an error occurs.

    If *ignore_errors* is set to ``True``, no errors will be printed.
    """
    try:
        return world.env.run(until=world.env.process(generator))
    except (ConnectionError, RemoteException, SimulationError) as exc:
        if errback is not None:
            errback()

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


def sync_call(sim, funcname, args, kwargs):
    """
    Start a SimPy process to make the *func()* call to a simulator behave
    like it was synchronous.

    Return the result of the *func()* call.

    Raise an :exc:`~mosaik.exceptions.SimulationError` if an exception occurs.
    """

    # We have to start a SimPy process to make the "create()" call
    # behave like it was synchronous.
    def proc():
        try:
            func = getattr(sim.proxy, funcname)
            ret = yield func(*args, **kwargs)
            return ret
        except ConnectionError as e:
            err_msg = ('Simulator "%s" closed its connection while executing '
                       '%s(*%s, **%s)' % (sim.sid, funcname, args, kwargs))
            raise SimulationError(err_msg, e) from None

    return sync_process(proc(), sim._world)
