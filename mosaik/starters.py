"""Starters describe how mosaik instantiates or connects to simulators.

This module provides the abstract base class :class:`Starter`, and the
three concrete subclasses :class:`PythonStarter` for starting a
simulator by instantiating a :class:`~mosaik_api_v3.Simulator` subclass
in the running process, :class:`CmdStarter` for starting a simulator
by spawning a separate process, and :class:`ConnectStarter` for
connecting to a simulator running at some TCP/IP address.

These starters can be used by storing them in a ``SIM_CONFIG`` dict
mapping *simulator names* to :class:`Starter` objects. When such a
``SIM_CONFIG`` is given to the mosaik :class:`~mosaik.World` at
creation, instances of the simulators can be spawned by simply giving
the simulator name to the worlds :meth:`mosaik.World.start` method.
Alternatively, this method also accepts a :class:`Starter` object
directly. (In this case, you need to specify the simulator ID, as it
cannot be auto-generated from the simulator name.)

Finally, traditionally, ``SIM_CONFIG`` would be a dict of dicts, where
the inner dicts correspond to our :class:`Starter` objects. To keep
supporting this, :class:`Starter` objects can be parsed from such a dict
using the :meth:`~Starter.from_starter_config` method; to try parsing
into all starters automatically, use
:func:`get_starter_from_starter_config`.
"""

from __future__ import annotations

import asyncio
import importlib
import os
import platform
import shlex
import subprocess
import sys
import warnings
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Union, cast

import mosaik_api_v3
from mosaik_api_v3.connection import Channel

from mosaik.exceptions import ScenarioError, SimulationError
from mosaik.proxies import BaseProxy, LocalProxy, RemoteProxy
from mosaik.simmanager import MosaikRemote

if TYPE_CHECKING:
    from mosaik.async_scenario import MosaikConfigTotal, StarterConfig


class Starter(ABC):
    """Description of how to start or connect to a mosaik simulator.

    In practice, you will usually use one of the subclasses
    :class:`PythonStarter`, :class:`CmdStarter`, or
    :class:`ConnectStarter`.
    """

    api_version: str | None
    """The API version of this simulator. This should be set if the
    simulator is using an outdated version of the API.
    """

    @abstractmethod
    async def start(
        self,
        sim_id: mosaik_api_v3.SimId,
        mosaik_remote: MosaikRemote,
        mosaik_config: MosaikConfigTotal,
    ) -> BaseProxy:
        """Start the simulator as described by this Starter under the
        name ``sim_id`` and using the supplied ``mosaik_remote`` to
        allow it to make callbacks to mosaik.

        This may raise :class:`ScenarioError` (or appropriate
        subclasses) if the simulator cannot be started.
        """

    @classmethod
    @abstractmethod
    def from_starter_config(cls, starter_config: StarterConfig) -> Starter | None:
        """Attempt to create a starter from the given StarterConfig.
        If the StarterConfig does not match this type of Starter, return
        ``None`` to indicate that a different Starter should be tried.
        """

    @classmethod
    def from_sim_config_entry(cls, entry: Union[StarterConfig, Starter]) -> Starter:
        """Create a :class:`Starter` from an entry in a
        :class:`~mosaik.async_scenario.SimConfig`. This is intended to
        be called on a subclass of :class:`Starter` and will check that
        the given ``entry`` is either already an instance of that
        subclass or that it can be parsed into one by that subclass's
        :meth:`from_starter_config` method.

        This is a convenience method if you already have a
        ``SimConfig``. In most cases, you will either construct starters
        directly or use :func:`get_starter_from_starter_config`,
        instead.
        """
        if isinstance(entry, Starter):
            if not isinstance(entry, cls):
                raise TypeError(
                    "when passing a Starter to from_sim_config, it must match the "
                    "Starter subclass specified"
                )
            return entry
        starter = cls.from_starter_config(entry)
        if not starter:
            raise ValueError(
                "the given entry does not specify a Starter of the specified "
                "Starter subclass"
            )
        return starter


class PythonStarter(Starter):
    """Description of how to start a simulator based on its
    mosaik_api_v3.Simulator class.

    In traditional mosaik, this starter corresponds to a ``"python"``
    entry in the :class:`~mosaik.async_scenario.SimConfig`, and it
    can be constructed from such an entry using
    :meth:`from_starter_config`.
    """

    cls: type[mosaik_api_v3.Simulator]
    """The :class:`~mosaik_api_v3.Simulator` subclass started by this
    starter. When started, the class's constructor will be called with
    :attr:`args` and :attr:`kwargs`."""
    args: tuple[Any, ...]
    """The args to give to the constructor of the simulator."""
    kwargs: dict[str, Any]
    """The kwargs to give to the constructor of the simulator."""

    def __init__(
        self,
        cls: type[mosaik_api_v3.Simulator],
        *,
        api_version: str | None = None,
        args: tuple[Any, ...] = (),
        kwargs: dict[str, Any] = {},
    ):
        self.cls = cls
        self.api_version = api_version
        # TODO: allow setting these
        self.args = args
        self.kwargs = kwargs

    async def start(
        self,
        sim_id: mosaik_api_v3.SimId,
        mosaik_remote: MosaikRemote,
        mosaik_config: MosaikConfigTotal,
    ) -> BaseProxy:
        return LocalProxy(self.cls(*self.args, **self.kwargs), mosaik_remote)

    @classmethod
    def from_module_class_name(
        cls, mod_name: str, cls_name: str, *, api_version: str | None = None
    ) -> PythonStarter:
        """Attemp to import the simulator class ``cls_name`` from the
        module ``mod_name``, and return a ``PythonStarter`` using this
        class if successful.
        """
        try:
            mod = importlib.import_module(mod_name)
            sim_cls = getattr(mod, cls_name)
        except (AttributeError, ImportError) as err:
            detail_msgs = {
                ModuleNotFoundError: f"could not import module `{mod_name}`",
                AttributeError: f"class `{cls_name}` not found in module `{mod_name}`",
                ImportError: f"Error importing the requested class: {err.args[0]}",
            }
            details = detail_msgs[type(err)]
            raise ScenarioError(f"Simulator could not be started: {details}")

        if int(mosaik_api_v3.__version__.split(".")[0]) < 3:
            raise ScenarioError("mosaik 3 requires mosaik_api_v3 or newer.")

        return cls(sim_cls, api_version=api_version)

    @classmethod
    def from_string(
        cls, import_string: str, *, api_version: str | None = None
    ) -> PythonStarter:
        """Attempt to import the a simulator class based on
        ``import_string``: It should follow the form
        `"module_name:ClassName"` (note the colon instead of a dot).
        Return a :class:`PythonStarter` if successful.
        """
        try:
            mod_name, cls_name = import_string.split(":")
        except ValueError:
            raise ScenarioError(
                'malformed import string for python starter, expected "module:Class"'
            )

        return cls.from_module_class_name(mod_name, cls_name, api_version=api_version)

    @classmethod
    def from_starter_config(cls, starter_config: StarterConfig) -> Starter | None:
        if import_string := starter_config.get("python"):
            return cls.from_string(
                import_string, api_version=starter_config.get("api_version")
            )
        return None


class CmdStarter(Starter):
    """Description of how to start a simulator in a new process.

    In traditional mosaik, this starter corresponds to a ``"cmd"``
    entry in the :class:`~mosaik.async_scenario.SimConfig`, and it
    can be constructed from such an entry using
    :meth:`from_starter_config`.
    """

    cmd: str
    """The command to start the process"""
    posix: bool
    """Whether we are running on a POSIX machine (for parsing the
    ``cmd``)
    """
    cwd: str
    """The current working directory for the started simulator"""
    env: dict[str, str]
    """Additional enviroment variables (will be joined with our own)"""
    new_console: bool
    """Whether to open a new console for this simulator (only works on
    Windows)
    """
    auto_terminate: bool
    """Whether to automatically terminate the process when the world
    is shut down"""

    bind_addr: tuple[str, int | None] | None
    connect_timeout: float | None

    def __init__(
        self,
        cmd: str,
        *,
        api_version: str | None = None,
        auto_terminate: bool = True,
        bind_addr: tuple[str, int | None] | None = None,
        connect_timeout: float | None = None,
        cwd: str = ".",
        env: dict[str, str] = {},
        new_console: bool = False,
        posix: bool = os.name == "nt",
    ):
        self.cmd = cmd
        self.posix = posix
        self.cwd = cwd
        self.env = env
        self.new_console = new_console
        self.auto_terminate = auto_terminate
        self.api_version = api_version
        self.bind_addr = bind_addr
        self.connect_timeout = connect_timeout

    async def start(
        self,
        sim_id: mosaik_api_v3.SimId,
        mosaik_remote: MosaikRemote,
        mosaik_config: MosaikConfigTotal,
    ) -> BaseProxy:
        channel_future: asyncio.Future[Channel] = asyncio.Future()

        async def on_connect(r: asyncio.StreamReader, w: asyncio.StreamWriter):
            channel_future.set_result(Channel(r, w, name=sim_id))

        bind_addr = self.bind_addr or mosaik_config["addr"]
        server = await asyncio.start_server(on_connect, *bind_addr)
        try:
            actual_addr = server.sockets[0].getsockname()

            replacements = {
                "addr": "%s:%s" % actual_addr,
                "python": sys.executable,
            }
            cmd = self.cmd % replacements
            cmd_parts = shlex.split(cmd, posix=bool(self.posix))

            # Make a copy of the current env vars dictionary and update
            # it with the user provided values
            environ = {
                **dict(os.environ),
                **self.env,
            }  # replacement for dict.union (or |) in Python 3.8

            # CREATE_NEW_CONSOLE constant for subprocess is only
            # available on Windows
            creationflags: int = 0
            if self.new_console:
                if "Windows" in platform.system():
                    creationflags = cast(int, subprocess.CREATE_NEW_CONSOLE)  # type: ignore
                else:
                    warnings.warn(
                        f'Simulator "{sim_id}" could not be started in a new console: '
                        "Only available on Windows"
                    )

            try:
                proc = subprocess.Popen(
                    cmd_parts,
                    bufsize=1,
                    cwd=self.cwd,
                    universal_newlines=True,
                    env=environ,  # pass the new env dict to the sub process
                    creationflags=creationflags,
                )
            except (FileNotFoundError, NotADirectoryError) as e:
                # This distinction has to be made due to a change in
                # Python 3.8.0. It might become unecessary for future
                # releases supporting Python >= 3.8 only.
                if str(e).count(":") == 2:
                    eout = e.args[1]
                else:
                    eout = str(e).split("] ")[1]
                raise ScenarioError(
                    f'Simulator "{sim_id}" could not be started: {eout}'
                ) from None

            try:
                channel = await asyncio.wait_for(
                    channel_future,
                    timeout=self.connect_timeout or mosaik_config["start_timeout"],
                )
                return RemoteProxy(
                    channel,
                    mosaik_remote,
                    process=(proc, self.auto_terminate),
                )
            except asyncio.TimeoutError:
                if self.auto_terminate:
                    proc.terminate()
                raise SimulationError(
                    f'Simulator "{sim_id}" did not connect to mosaik in time.'
                )
        finally:
            server.close()

    @classmethod
    def from_starter_config(cls, starter_config: StarterConfig) -> Starter | None:
        if "cmd" not in starter_config:
            return None

        return cls(**starter_config)


class ConnectStarter(Starter):
    """Description of how to "start" a simulator already running at some
    address by connecting to it.

    In traditional mosaik, this starter corresponds to a ``"connect"``
    entry in the :class:`~mosaik.async_scenario.SimConfig`, and it
    can be constructed from such an entry using
    :meth:`from_starter_config`.
    """

    host: str
    port: int

    def __init__(self, host: str, port: int, *, api_version: str | None = None):
        self.host = host
        self.port = port
        self.api_version = api_version

    async def start(
        self,
        sim_id: mosaik_api_v3.SimId,
        mosaik_remote: MosaikRemote,
        mosaik_config: MosaikConfigTotal,
    ) -> BaseProxy:
        try:
            reader, writer = await asyncio.open_connection(self.host, self.port)
        except (ConnectionError, OSError):
            raise SimulationError(
                f'Simulator "{sim_id}" could not be started: Could not connect to '
                f'"{self.host}:{self.port}"'
            )
        return RemoteProxy(Channel(reader, writer, name=sim_id), mosaik_remote)

    @classmethod
    def from_addr_string(
        cls, address: str, *, api_version: str | None = None
    ) -> ConnectStarter:
        """Construct a :class:`ConnectStarter` from an address string in
        the format "host:port".
        """
        try:
            host, port_str = address.strip().split(":")
            port = int(port_str)
        except ValueError:
            raise ScenarioError(
                f'ConnectStarter could be created: Could not parse address "{address}"'
            )

        return cls(host, port, api_version=api_version)

    @classmethod
    def from_addr(
        cls, addr: str | tuple[str, int], *, api_version: str | None = None
    ) -> ConnectStarter:
        """Construct a :class:`ConnectStarter` from a host-port pair."""
        if isinstance(addr, str):
            return cls.from_addr_string(addr, api_version=api_version)
        else:
            return cls(*addr, api_version=api_version)

    @classmethod
    def from_starter_config(cls, starter_config: StarterConfig) -> Starter | None:
        if addr_string := starter_config.get("connect"):
            return cls.from_addr_string(
                addr_string, api_version=starter_config.get("api_version")
            )
        return None


STARTERS: list[type[Starter]] = [PythonStarter, CmdStarter, ConnectStarter]
"""The default starters used by mosaik.

You can add additional :class:`Starter` subclasses to this list to make
parsing their starter configs availabe in your
:class:`~mosaik.async_scenario.SimConfig`. Alternatively, your own
starters can also be used as entries in the ``SimConfig`` directly, or
be passed to
:meth:`world.start <mosaik.async_scenario.AsyncWorld.start>`
directly.
"""


def get_starter_from_starter_config(starter_config: StarterConfig) -> Starter:
    """Construct a :class:`Starter` from the given
    :class:`~mosaik.async_scenario.StarterConfig` by trying the
    ``Starter`` subclasses in :data:`STARTERS` one by one (using the
    :meth:`Starter.from_starter_config` method from each).
    """
    for starter_cls in STARTERS:
        starter = starter_cls.from_starter_config(starter_config)
        if starter:
            return starter
    else:
        raise ScenarioError(
            f"Starter config {starter_config} does not match any known starter. "
            '(By default, it must contain one of the keys "python", "cmd", or '
            '"connect".)'
        )
