from __future__ import annotations

import asyncio
import warnings
from asyncio.subprocess import Process
from typing import Protocol

from loguru import logger


class ProcessTerminationManager(Protocol):
    """A protocal for coroutines that can terminate an
    :class:`asyncio.subprocess.Process`.

    See :mod:`mosaik.process_termination.managers` for predefined
    termination managers.
    """

    async def __call__(self, process: Process):
        """Terminate the process (or not), as specified for this
        termination manager.
        """


async def keep_running(process: Process):
    """Do not attempt to terminate the process. (It might keep running
    depending on the operating system and the way that it was created.)
    """
    # Nothing to be done, just log the state
    rc = process.returncode
    if rc is not None:
        logger.trace("Simulator process is still running, keeping it that way")
    else:
        logger.trace(f"Simulator process has already concluded with exit code {rc}")


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
            logger.trace("Attempting to terminate simulator process.")
            process.terminate()
        except ProcessLookupError:
            # The process is already gone, so we're happy
            logger.trace("Simulator process had already ceased existing.")
            pass
        try:
            # If timeout is None, wait_for will wait indefinitely
            exit_code = await asyncio.wait_for(process.wait(), self.timeout)
            logger.trace(f"Simulator process finished with exit code {exit_code}")
        except asyncio.TimeoutError:
            warnings.warn(
                UserWarning(
                    f"simulator did not terminate within {self.timeout} seconds after "
                    "terminate call by mosaik. (Set `termination_manager=keep_running` "
                    "to stop mosaik from terminating the simulator at all; or "
                    "`termination_manager=auto_terminate(timeout=timeout)` to wait for "
                    "`timeout` seconds; `None` meaning indefinitely."
                )
            )
