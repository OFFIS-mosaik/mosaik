from __future__ import annotations

import asyncio
import warnings
from asyncio.subprocess import Process
from typing import Protocol


class ProcessTerminationManager(Protocol):
    """A protocal for coroutines that can terminate an
    :class:`asyncio.subprocess.Process`.

    See :mod:`mosaik.process_termination.managers` for predefined
    termination managers.
    """

    async def __call__(self, process: Process): ...


async def keep_running(process: Process):
    """Do not attempt to terminate the process. (It might keep running
    depending on the operating system an the way that it was created.)
    """
    # Nothing to be done
    pass


class auto_terminate:
    """Instances of this class terminate a process by sending it a
    `terminate` signal, then wait for it `timeout` seconds (or
    indefinitely if `timeout=None`.

    Note: This needs to be instanciated to get a
    `ProcessTerminationManager`.
    """

    timeout: float | None

    def __init__(self, timeout: float | None = None):
        self.timeout = timeout

    async def __call__(self, process: Process):
        try:
            process.terminate()
            if self.timeout is not None:
                await asyncio.wait_for(process.wait(), self.timeout)
            else:
                await process.wait()
        except ProcessLookupError:
            # The process is already gone, so we're happy
            pass
        except asyncio.TimeoutError:
            warnings.warn(
                UserWarning(
                    "mosaik could not terminate subprocess for cmd simulator "
                    "(set `auto_terminate=False` to stop it from trying)"
                )
            )
