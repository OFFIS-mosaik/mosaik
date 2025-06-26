"""Starters describe how mosaik instantiates or connects to simulators.

This module provides the abstract base class :class:`Starter`, and the
three concrete subclasses :class:`PythonStarter` for starting a
simulator by instantiating a :class:`~mosaik_api_v3.Simulator` subclass
in the running process, :class:`ProcStarter` for starting a simulator
by spawning a separate process, and :class:`ConnectStarter` for
connecting to a simulator running at some TCP/IP address.

These starters can be used by storing them in a ``SIM_CONFIG`` dict
mapping *simulator names* to :class:`Starter`s. When such a
``SIM_CONFIG`` is given to the mosaik :class:`~mosaik.World` at
creation, instances of the simulators can be spawned by simply giving
the simulator name to the worlds :meth:`mosaik.World.start` method.
Alternatively, this method also accepts a :class:`Starter` object
directly.

Finally, traditionally, ``SIM_CONFIG`` would be a dict of dicts, where
the inner dicts correspond to our :class:`Starter` objects. To keep
supporting this, :class:`Starter`s can be parsed from such a dict using
the :meth:`~Starter.from_model_config` method; to try parsing into all
starters automatically, use :func:`get_starter_from_model_config`.
"""

import asyncio
import importlib
import os
import platform
import shlex
import subprocess
import sys
import warnings
from abc import ABC, abstractmethod
from typing import Any, Self, cast

import mosaik_api_v3
from mosaik_api_v3.connection import Channel

from mosaik.async_scenario import ModelConfig, MosaikConfigTotal
from mosaik.exceptions import ScenarioError, SimulationError
from mosaik.proxies import BaseProxy, RemoteProxy
from mosaik.simmanager import MosaikRemote
from tests.test_simmanager import LocalProxy


class Starter(ABC):
    api_version: str | None

    @abstractmethod
    async def start(
        self, sim_id: mosaik_api_v3.SimId, mosaik_remote: MosaikRemote
    ) -> BaseProxy:
        """Start the simulator as described by this Starter under the
        name ``sim_id`` and using the supplied ``mosaik_remote`` to
        allow it to make callbacks to mosaik.

        This may raise :class:`ScenarioError` (or appropriate
        subclasses) if the simulator cannot be started.
        """

    @abstractmethod
    @classmethod
    def from_model_config(
        cls, model_config: ModelConfig, mosaik_config: MosaikConfigTotal
    ) -> Self | None:
        """Attempt to create a starter from the given ModelConfig.
        If the ModelConfig does not match this type of Starter, return
        ``None`` to indicate that a different Starter should be tried.
        """


class PythonStarter(Starter):
    """Description of how to start a simulator based on its
    mosaik_api_v3.Simulator class.
    """

    cls: type[mosaik_api_v3.Simulator]
    args: tuple[Any, ...]
    kwargs: dict[str, Any]

    def __init__(
        self, cls: type[mosaik_api_v3.Simulator], *, api_version: str | None = None
    ):
        self.cls = cls
        self.api_version = api_version
        # TODO: allow setting these
        self.args = ()
        self.kwargs = {}

    async def start(
        self, sim_id: mosaik_api_v3.SimId, mosaik_remote: MosaikRemote
    ) -> BaseProxy:
        return LocalProxy(self.cls(*self.args, **self.kwargs), mosaik_remote)

    @classmethod
    def from_module_class_name(cls, mod_name: str, cls_name: str) -> Self:
        """Attemp to import the simulator class ``cls_name`` from the
        module ``mod_name``, and return a ``PythonStarter`` using this
        class if successful.
        """
        try:
            mod = importlib.import_module(mod_name)
            sim_cls = getattr(mod, cls_name)
        except (AttributeError, ImportError) as err:
            detail_msgs = {
                ModuleNotFoundError: f"Could not import module: {err.args[0]}",
                AttributeError: "Class not found in module",
                ImportError: f"Error importing the requested class: {err.args[0]}",
            }
            details = detail_msgs[type(err)]
            raise ScenarioError(f"Simulator could not be started: {details}")

        if int(mosaik_api_v3.__version__.split(".")[0]) < 3:
            raise ScenarioError("Mosaik 3 requires mosaik_api_v3 or newer.")

        return cls(sim_cls)

    @classmethod
    def from_string(cls, import_string: str) -> Self:
        """Attempt to import the a simulator class based on
        ``import_string``: It should follow the form
        `"module_name:ClassName"` (note the colon instead of a dot).
        Return a :class:`PythonStarter` if successful.
        """
        try:
            mod_name, cls_name = import_string.split(":")
        except ValueError:
            raise ScenarioError('Malformed Python class name: Expected "module:Class"')

        return cls.from_module_class_name(mod_name, cls_name)

    @classmethod
    def from_model_config(
        cls, model_config: ModelConfig, mosaik_config: MosaikConfigTotal
    ) -> Self | None:
        if import_string := model_config.get("python"):
            return cls.from_string(import_string)
        return None


class CmdStarter(Starter):
    """Description of how to start a simulator in a new process."""

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
    api_version: str | None
    """The expected API version of this simulator"""

    bind_addr: tuple[str, int | None]
    connect_timeout: float

    def __init__(
        self,
        cmd: str,
        *,
        api_version: str | None = None,
        auto_terminate: bool = True,
        bind_addr: tuple[str, int | None],
        connect_timeout: float,
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
        self, sim_id: mosaik_api_v3.SimId, mosaik_remote: MosaikRemote
    ) -> BaseProxy:
        channel_future: asyncio.Future[Channel] = asyncio.Future()

        async def on_connect(r: asyncio.StreamReader, w: asyncio.StreamWriter):
            channel_future.set_result(Channel(r, w, name=sim_id))

        server = await asyncio.start_server(on_connect, *self.bind_addr)
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
            environ = dict(os.environ) | self.env

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
                    channel_future, timeout=self.connect_timeout
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
    def from_model_config(
        cls, model_config: ModelConfig, mosaik_config: MosaikConfigTotal
    ) -> Self | None:
        if "cmd" not in model_config:
            return None

        return cls(
            **model_config,
            bind_addr=mosaik_config["addr"],
            connect_timeout=mosaik_config["start_timeout"],
        )


class ConnectStarter(Starter):
    """Description of how to "start" a simulator already running at some
    address by connecting to it.
    """

    host: str
    port: int

    def __init__(self, host: str, port: int, *, api_version: str | None = None):
        self.host = host
        self.port = port
        self.api_version = api_version

    async def start(
        self, sim_id: mosaik_api_v3.SimId, mosaik_remote: MosaikRemote
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
    def from_addr_string(cls, address: str, *, api_version: str | None = None) -> Self:
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
    ) -> Self:
        if isinstance(addr, str):
            return cls.from_addr_string(addr, api_version=api_version)
        else:
            return cls(*addr, api_version=api_version)

    @classmethod
    def from_model_config(
        cls, model_config: ModelConfig, mosaik_config: MosaikConfigTotal
    ) -> Self | None:
        if addr_string := model_config.get("connect"):
            return cls.from_addr_string(
                addr_string, api_version=model_config.get("api_version")
            )
        return None


STARTERS: list[type[Starter]] = [PythonStarter, CmdStarter, ConnectStarter]


def get_starter_from_model_config(
    model_config: ModelConfig, mosaik_config: MosaikConfigTotal
) -> Starter:
    for starter_cls in STARTERS:
        starter = starter_cls.from_model_config(model_config, mosaik_config)
        if starter:
            return starter
    else:
        raise ScenarioError(
            f"Model config {model_config} does not match any known starter. "
            "(By default, it must contain one of the keys 'python', 'cmd', or "
            "'connect'.)"
        )
