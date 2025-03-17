from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from copy import deepcopy
from inspect import isgeneratorfunction
from subprocess import Popen
from typing import Any, Dict, Iterator, List, Tuple

from loguru import logger
from mosaik_api_v3 import MosaikProxy, Simulator, check_api_compliance
from mosaik_api_v3.connection import Channel, EndOfRequests
from mosaik_api_v3.types import Meta, SimId

from mosaik.exceptions import ScenarioError


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
        of a function name, a list of positional arguments and a dict
        of named arguments.
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
    more ``Adapter``s to allow treating the simulator as up-to-date from
    other parts of mosaik.
    """

    @abstractmethod
    async def init(
        self, sid: SimId, *, time_resolution: float, **sim_params: Any
    ) -> List[int]:
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
    """The underlying ``mosaik_api.Simulator."""

    def __init__(self, sim: Simulator, mosaik_remote: MosaikProxy):
        super().__init__()
        self.sim = sim
        sim.mosaik = mosaik_remote

    async def init(self, sid: SimId, **kwargs: Any) -> List[int]:
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
            raise ScenarioError(
                "The underlying simulator is not compliant with the high-level API "
                "version 3 (or higher) (because its init method is missing the "
                "time_resolution keyword parameter or its step method is missing the "
                "max_advance parameter), but it claims to be of version "
                f"{'.'.join(map(str, version))} in its meta's api_version field."
            )
        return version

    @property
    def meta(self):
        return self._meta

    async def send(self, request: Tuple[str, Tuple[Any, ...], Dict[str, Any]]):
        func_name, args, kwargs = request
        func = getattr(self.sim, func_name)
        # A simulator that makes requests back to mosaik (like set_data
        # or set_event) will have generator functions instead of normal
        # functions as its init, create, step and/or get_data. It will
        # yield coroutines that produce the required information, which
        # we have to await. (This is due to simpy, which used generator
        # functions for its asynchronicity; we didn't want to break the
        # API.)
        # TODO: Maybe check this during __init__ and create the right
        # methods instead of checking for isgeneratorfunction on each
        # call?
        if isgeneratorfunction(func):
            gen = func(*args, **kwargs)
            try:
                incoming_request = next(gen)
                while True:
                    incoming_request = gen.send(await incoming_request)
            except StopIteration as stop:
                return stop.value
        else:
            return func(*args, **kwargs)

    async def stop(self):
        self.sim.finalize()


class RemoteProxy(BaseProxy):
    _channel: Channel
    _reader_task: asyncio.Task[None]
    _outgoing_msg_counter: Iterator[int]
    _mosaik_remote: MosaikProxy
    _process: Tuple[Popen[str], bool] | None
    """The process for this RemoteProxy (or None, if the connection
    was established using connect). The second component of the tuple is
    True if the process should be automatically terminated at the end of
    the simulation.
    """

    def __init__(
        self,
        channel: Channel,
        mosaik_remote: MosaikProxy,
        *,
        process: Tuple[Popen[str], bool] | None = None,
    ):
        super().__init__()
        self._channel = channel
        self._mosaik_remote = mosaik_remote
        self._reader_task = asyncio.create_task(
            self._handle_remote_requests(), name="handle remote requests for ???"
        )
        self._process = process

    async def _handle_remote_requests(self) -> None:
        try:
            while True:
                request = await self._channel.next_request()
                func_name, args, kwargs = request.content
                func = getattr(self._mosaik_remote, func_name)
                try:
                    result = await func(*args, **kwargs)
                    await request.set_result(result)
                except Exception as e:
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
        except Exception as e:
            logger.exception(
                "Something went wrong in _handle_remote_requests, "
                f"exception type {type(e)}"
            )
            await self.stop()

    async def init(self, sid: SimId, **kwargs: Any) -> List[int]:
        self._meta = await self.send(["init", (sid,), kwargs])
        return extract_version(self._meta)

    @property
    def meta(self) -> Meta:
        return self._meta

    async def send(self, request: Any) -> Any:
        return await self._channel.send(request)

    async def stop(self) -> None:
        try:
            await asyncio.wait_for(self._channel.send(["stop", [], {}]), 0.1)
        except (asyncio.TimeoutError, asyncio.IncompleteReadError):
            pass
        await self._channel.close()
        await self._reader_task
        if self._process and self._process[1]:
            self._process[0].terminate()


def extract_version(meta: Meta) -> List[int]:
    if "api_version" not in meta:
        return [1]
    else:
        return list(map(int, meta["api_version"].split(".")))
