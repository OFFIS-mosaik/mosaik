"""This module contains the :class:`Proxy` class and its subclasses.
They are used to represent a running simulator in the scenario.
:class:`LocalProxy` represents a simulator running in the current
Python process; :class:`RemoteProxy` represents a simulator connected to
mosaik via a TCP connection.
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from collections.abc import Iterator
from copy import deepcopy
from inspect import isgeneratorfunction
from typing import TYPE_CHECKING, Any

from loguru import logger
from mosaik_api_v3 import MosaikProxy, Simulator, check_api_compliance
from mosaik_api_v3.connection import Channel, EndOfRequests
from mosaik_api_v3.types import Meta, SimId

from mosaik.exceptions import ConnectionClosedError, ForcedOldApiUsageError
from mosaik.process_termination_managers import ProcessTerminationManager

if TYPE_CHECKING:
    from mosaik.simmanager import MosaikRemote


def _trace_call(log: Any, direction: str, method: str, args: Any, kwargs: Any) -> None:
    """Trace a call while leaving argument rendering to loguru."""
    parameters = ["{!r}"] * len(args)
    parameters.extend(f"{name}={{!r}}" for name in kwargs)
    log.trace(
        f"{direction}: {method}({', '.join(parameters)})",
        *args,
        *kwargs.values(),
    )


class _TracingMosaikProxy(MosaikProxy):
    """Add tracing to calls a simulator makes back to mosaik."""

    def __init__(self, remote: MosaikProxy, log: Any):
        self._remote = remote
        self._log = log

    async def _send(self, request: Any) -> Any:
        method, args, kwargs = request
        _trace_call(self._log, "simulator -> mosaik", method, args, kwargs)
        try:
            result = await getattr(self._remote, method)(*args, **kwargs)
        except Exception as exception:
            self._log.trace("mosaik -> simulator: {} raised {!r}", method, exception)
            raise
        self._log.trace("mosaik -> simulator: {} returned {!r}", method, result)
        return result

    async def get_progress(self) -> float:
        return await self._send(("get_progress", (), {}))

    async def get_related_entities(self, entities: Any = None) -> Any:
        return await self._send(("get_related_entities", (entities,), {}))

    async def get_data(self, attrs: Any) -> Any:
        return await self._send(("get_data", (attrs,), {}))

    async def set_data(self, data: Any) -> None:
        await self._send(("set_data", (data,), {}))

    async def set_event(self, event_time: Any) -> None:
        await self._send(("set_event", (event_time,), {}))


class Proxy(ABC):
    """A proxy for a mosaik simulator from the view of a mosaik
    scenario.

    Generally, this will be a ``BaseProxy`` subclass wrapped in the
    appropriate ``Adapter`` subclasses to bring the interface of the
    connected simulator in line with the most up-to-date API version.
    """

    @abstractmethod
    async def send(self, request: Any) -> Any:
        """Send a request to the connected simulator.

        :param request: Generally, this will be a three-tuple consisting
            of a function name, a list of positional arguments and a
            dict of named arguments.
        :return: The return value from the remote simulator (depends on
            the specified function).
        """
        raise NotImplementedError()

    @property
    @abstractmethod
    def meta(self) -> Meta:
        """The meta of the connected simulator, as adapted by the
        adapters.
        """
        raise NotImplementedError()

    @abstractmethod
    async def stop(self) -> None:
        """Stop the connected simulator. This is not handled via
        ``send`` as there are extra steps to be taken to close the
        connection cleanly.
        """
        raise NotImplementedError()


class BaseProxy(Proxy):
    """A base ``Proxy`` for a connected simulator that simply sends all
    requests along unchanged. This will usually be wrapped in one or
    more instances of ``Adapter`` to allow treating the simulator as
    up-to-date from other parts of mosaik.
    """

    @abstractmethod
    async def init(
        self, sid: SimId, *, time_resolution: float, **sim_params: Any
    ) -> list[int]:
        """Initialize the simulator by sending the ``init`` call. The
        ``meta`` returned by the simulator will be saved to be retrieved
        using the ``meta`` property.

        :param sid: The ``SimId`` that mosaik assigns to this simulator
            instance
        :param time_resolution: The time resolution of the simulation,
            i.e. how many seconds correspond to one mosaik time step.
        :param sim_params: The params sent to the simulator for
            initialization.
        """
        raise NotImplementedError()


class LocalProxy(BaseProxy):
    """
    Proxy for a local simulator. This mainly wraps each mosaik method in
    a coroutine.
    """

    sim: Simulator
    """The underlying :class:`mosaik_api_v3.Simulator`."""

    def __init__(self, sim: Simulator, mosaik_remote: MosaikProxy):
        super().__init__()
        self.sim = sim
        self._log = logger.bind(
            simulator=f"sim.local.{getattr(mosaik_remote, 'sid', 'unknown')}"
        )
        sim.mosaik = _TracingMosaikProxy(mosaik_remote, self._log)

    async def init(self, sid: SimId, **kwargs: Any) -> list[int]:
        # This in an ugly place for these checks. However, we cannot
        # put them in mosaik.adapters because we need to determine
        # API compliance before sending the init method and thus before
        # receiving the version number to build the adapter.
        if check_api_compliance(self.sim):
            forced_old_api = False
        else:
            forced_old_api = True
            del kwargs["time_resolution"]

        meta = await self.send(("init", (sid,), kwargs))
        self._meta = deepcopy(meta)
        version = extract_version(meta)
        if forced_old_api and version >= [3]:
            raise ForcedOldApiUsageError(sid, version)
        return version

    @property
    def meta(self):
        return self._meta

    async def send(self, request: tuple[str, tuple[Any, ...], dict[str, Any]]):
        func_name, args, kwargs = request
        _trace_call(self._log, "mosaik -> simulator", func_name, args, kwargs)
        try:
            func = getattr(self.sim, func_name)
            # A simulator that makes requests back to mosaik (like
            # set_data or set_event) will have generator functions
            # instead of normal functions as its init, create, step
            # and/or get_data. It will yield coroutines that produce the
            # required information, which we have to await. (This is due
            # to simpy, which used generator functions for its
            # asynchronicity; we didn't want to break the API.)
            # TODO: Maybe check this during __init__ and create the
            # right methods instead of checking for
            # isgeneratorfunction on each call?
            if isgeneratorfunction(func):
                gen = func(*args, **kwargs)
                try:
                    incoming_request = next(gen)
                    while True:
                        incoming_request = gen.send(await incoming_request)
                except StopIteration as stop:
                    result = stop.value
            else:
                result = func(*args, **kwargs)
        except Exception as exception:
            self._log.trace("simulator -> mosaik: {} raised {!r}", func_name, exception)
            raise
        self._log.trace("simulator -> mosaik: {} returned {!r}", func_name, result)
        return result

    async def stop(self):
        _trace_call(self._log, "mosaik -> simulator", "finalize", (), {})
        try:
            result = self.sim.finalize()
        except Exception as exception:
            self._log.trace("simulator -> mosaik: finalize raised {!r}", exception)
            raise
        self._log.trace("simulator -> mosaik: finalize returned {!r}", result)


class RemoteProxy(BaseProxy):
    _channel: Channel
    _reader_task: asyncio.Task[None]
    _outgoing_msg_counter: Iterator[int]
    _mosaik_remote: MosaikRemote
    _process: tuple[asyncio.subprocess.Process, ProcessTerminationManager] | None
    """The process for this RemoteProxy (or None, if the connection
    was established using connect). The second component of the tuple is
    a ProcessTerminationManager: a function that is called with the
    process as the first argument that is responsible for terminating
    the process in the desired way (which might depend on the simulator
    and simulation).
    """

    def __init__(
        self,
        channel: Channel,
        mosaik_remote: MosaikRemote,
        *,
        process: tuple[asyncio.subprocess.Process, ProcessTerminationManager]
        | None = None,
    ):
        super().__init__()
        self._channel = channel
        self._log = logger.bind(simulator=f"sim.remote.{mosaik_remote.sid}")
        self._mosaik_remote = mosaik_remote
        self._reader_task = asyncio.create_task(
            self._handle_remote_requests(),
            name=f"handle remote requests for {mosaik_remote.sid}",
        )
        self._process = process

    async def _handle_remote_requests(self) -> None:
        try:
            while True:
                request = await self._channel.next_request()
                func_name, args, kwargs = request.content
                _trace_call(self._log, "simulator -> mosaik", func_name, args, kwargs)
                func = getattr(self._mosaik_remote, func_name)
                try:
                    result = await func(*args, **kwargs)
                    self._log.trace(
                        "mosaik -> simulator: {} returned {!r}", func_name, result
                    )
                    await request.set_result(result)
                except Exception as e:  # noqa: BLE001
                    self._log.trace("mosaik -> simulator: {} raised {!r}", func_name, e)
                    await request.set_exception(e)
        except EndOfRequests:
            pass
        except RuntimeError as e:
            if e.args[0] != "Event loop is closed":
                logger.exception(
                    "Something went wrong in _handle_remote_requests, "
                    f"exception type {type(e)}"
                )
                await self.stop()
        except Exception as e:  # noqa: BLE001
            logger.exception(
                "Something went wrong in _handle_remote_requests, "
                f"exception type {type(e)}"
            )
            await self.stop()

    async def init(self, sid: SimId, **kwargs: Any) -> list[int]:
        self._meta = await self.send(["init", (sid,), kwargs])
        return extract_version(self._meta)

    @property
    def meta(self) -> Meta:
        return self._meta

    async def send(self, request: Any) -> Any:
        method, args, kwargs = request
        _trace_call(self._log, "mosaik -> simulator", method, args, kwargs)
        try:
            result = await self._channel.send(request)
        except asyncio.IncompleteReadError as exception:
            raise ConnectionClosedError(
                simulator=self._channel._name or "unknown simulator",
                method_called=method,
            ) from exception
        except Exception as exception:
            self._log.trace("simulator -> mosaik: {} raised {!r}", method, exception)
            raise
        self._log.trace("simulator -> mosaik: {} returned {!r}", method, result)
        return result

    async def stop(self) -> None:
        request: list[Any] = ["stop", [], {}]
        _trace_call(self._log, "mosaik -> simulator", "stop", (), {})
        try:
            result = await asyncio.wait_for(self._channel.send(request), 0.1)
        except (TimeoutError, asyncio.IncompleteReadError, ConnectionResetError):
            pass
        else:
            self._log.trace("simulator -> mosaik: stop returned {!r}", result)
        await self._channel.close()
        await self._reader_task
        if self._process:
            process, terminate = self._process
            await terminate(process)


def extract_version(meta: Meta) -> list[int]:
    if "api_version" not in meta:
        return [1]
    else:
        return list(map(int, meta["api_version"].split(".")))
