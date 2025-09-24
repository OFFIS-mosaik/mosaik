from __future__ import annotations

import asyncio
import os
import sys
from subprocess import TimeoutExpired
from typing import Any, Callable, Coroutine, Type

import mosaik_api_v3.connection
import pytest
import pytest_asyncio
from example_sim.mosaik import ExampleSim
from mosaik_api_v3.connection import Channel, RemoteException

from mosaik import World, async_scenario, proxies, scenario, simmanager
from mosaik.exceptions import (
    DuplicateEntityIdError,
    NonSerializableOutputsError,
    ScenarioError,
)
from mosaik.proxies import BaseProxy, LocalProxy, RemoteProxy
from mosaik.tiered_time import TieredDuration, TieredTime

VENV = os.path.dirname(sys.executable)

SIM_CONFIG: scenario.SimConfig = {
    "ExampleSimA": {
        "python": "example_sim.mosaik:ExampleSim",
    },
    "ExampleSimB": {
        "cmd": f"{VENV}/pyexamplesim %(addr)s",
        "cwd": ".",
    },
    "ExampleSimC": {
        "connect": "127.0.0.1:5556",
    },
    "ExampleSimD": {},  # type: ignore  # this is used for testing for this error
    "Fail": {
        "cmd": '%(python)s -c "import time; time.sleep(0.2)"',
    },
    "ProcTestTrue": {
        "cmd": "%(python)s -m tests.simulators.proc_test_sim %(addr)s",
        "auto_terminate": True,
    },
    "ProcTestFalse": {
        "cmd": "%(python)s -m tests.simulators.proc_test_sim %(addr)s",
        "auto_terminate": False,
    },
    "SimulatorMock": {
        "python": "tests.simulators.simulator_mock:SimulatorMock",
    },
    "MetaMock": {
        "python": "tests.simulators.meta_mirror:MetaMirror",
    },
    "FixedOutputSim": {
        "python": "tests.simulators.fixed_output_sim:FixedOutputSim",
    },
    "EchoSim": {
        "python": "tests.simulators.loop_simulators.echo_simulator:EchoSim",
    },
}


@pytest.fixture(name="world")
def world_fixture():
    with scenario.World(SIM_CONFIG) as world:
        yield world


@pytest_asyncio.fixture
async def async_world():
    async with async_scenario.AsyncWorld(SIM_CONFIG) as world:
        yield world


def test_start_wrong_api_version(world: World, monkeypatch):
    """
    An exception should be raised if the simulator uses an unsupported
    API version."""
    with pytest.raises(ScenarioError) as exc_info:
        world.start("MetaMock", meta={"api_version": "1000.0"})

    assert str(exc_info.value) == (
        "There was an error during the initialization of MetaMock-0: The API version "
        "(1000.0) is too new for this version of mosaik. Maybe a newer version of the "
        "mosaik package is available to be used in your scenario?"
    )


@pytest.mark.parametrize("auto_terminate", [True, False])
def test_start_proc_auto_terminate(auto_terminate: bool):
    with World(
        {
            "ProcTest": {
                "cmd": "%(python)s -m tests.simulators.proc_test_sim %(addr)s",
                "auto_terminate": auto_terminate,
            }
        }
    ) as world:
        sim = world.start("ProcTest")
        world.run(1)

    proxy = sim._async_model_factory._proxy
    assert isinstance(proxy, RemoteProxy)
    assert proxy._process is not None
    try:
        proxy._process[0].wait(0.1)
    except TimeoutExpired:
        # Just wait a moment for terminate to go through, but not long
        # enough for the thread in ProcTest to finish.
        # This way, the process should only terminate if explicitly
        # terminated by mosaik.
        pass
    # Check that the process has terminated
    assert (proxy._process[0].poll() is not None) == auto_terminate


async def read_message(reader: asyncio.StreamReader):
    length = int.from_bytes(await reader.readexactly(4), "big")
    return await reader.readexactly(length)


@pytest.mark.filterwarnings("ignore:Simulator MetaMock")
def test_sim_proxy_illegal_model_names(world):
    with pytest.raises(ScenarioError):
        world.start("MetaMock", meta={"models": {"step": {}}})


@pytest.mark.filterwarnings("ignore:Simulator MetaMock")
def test_sim_proxy_illegal_extra_methods(world):
    with pytest.raises(ScenarioError):
        world.start("MetaMock", meta={"models": {}, "extra_methods": ["step"]})
    with pytest.raises(ScenarioError):
        world.start(
            "MetaMock", meta={"models": {"A": {"attrs": []}}, "extra_methods": ["A"]}
        )


def test_sim_proxy_stop_impl(world):
    class Test(BaseProxy):
        def init(self):
            raise NotImplementedError()

        def stop(self):
            raise NotImplementedError()

        async def send(self, *args, **kwargs):
            raise NotImplementedError()

        meta = {"type": "time-based", "models": {}}

    sim = simmanager.SimRunner("id", Test(), None)
    with pytest.raises(NotImplementedError):
        world.loop.run_until_complete(sim.stop())


def test_local_process(world):
    es = ExampleSim()
    proxy = LocalProxy(es, None)
    world.loop.run_until_complete(proxy.init("ExampleSim-0", time_resolution=1.0))
    sim = simmanager.SimRunner("ExampleSim-0", proxy, None)
    assert sim.sid == "ExampleSim-0"
    assert sim._proxy.sim is es
    assert sim.last_step == TieredTime(-1)
    assert sim.next_steps == [TieredTime(0)]


def test_local_process_finalized(world: World):
    """
    Test that ``finalize()`` is called for local processes (issue #23).
    """
    simulator = world.start("SimulatorMock")
    assert simulator._proxy.sim.finalized is False
    world.run(until=1)
    world.shutdown()
    assert simulator._proxy.sim.finalized is True


async def _rpc_get_progress(channel: Channel, world: World):
    """
    Helper for :func:`test_mosaik_remote()` that checks the
    "get_progress()" RPC.
    """
    progress = await channel.send(["get_progress", [], {}])
    assert progress == 23


async def _rpc_get_related_entities(channel: Channel, world: World):
    """
    Helper for :func:`test_mosaik_remote()` that checks the
    "get_related_entities()" RPC.
    """
    # No param yields complete entity graph
    entities = await channel.send(["get_related_entities", [], {}])
    for edge in entities["edges"]:
        edge[:2] = sorted(edge[:2])
    entities["edges"].sort()
    assert entities == {
        "nodes": {
            "X.0": {"sim": "ExampleSim", "type": "A"},
            "X.1": {"sim": "ExampleSim", "type": "A"},
            "X.2": {"sim": "ExampleSim", "type": "A"},
            "X.3": {"sim": "ExampleSim", "type": "A"},
        },
        "edges": [
            ["X.0", "X.1", {}],
            ["X.0", "X.2", {}],
            ["X.1", "X.2", {}],
            ["X.2", "X.3", {}],
        ],
    }

    # Single string yields dict with related entities
    entities = await channel.send(["get_related_entities", ["X.0"], {}])
    assert entities == {
        "X.1": {"sim": "ExampleSim", "type": "A"},
        "X.2": {"sim": "ExampleSim", "type": "A"},
    }

    # List of strings yields dicts with related entities grouped by
    # input ids
    entities = await channel.send(["get_related_entities", [["X.1", "X.2"]], {}])
    assert entities == {
        "X.1": {
            "X.0": {"sim": "ExampleSim", "type": "A"},
            "X.2": {"sim": "ExampleSim", "type": "A"},
        },
        "X.2": {
            "X.0": {"sim": "ExampleSim", "type": "A"},
            "X.1": {"sim": "ExampleSim", "type": "A"},
            "X.3": {"sim": "ExampleSim", "type": "A"},
        },
    }


async def _rpc_get_data(channel: Channel, world: World):
    """
    Helper for :func:`test_mosaik_remote()` that checks the "get_data()"
    RPC.
    """
    data = await channel.send(["get_data", [{"X.2": ["attr"]}], {}])
    assert data == {"X.2": {"attr": "val"}}


async def _rpc_set_data(channel: Channel, world: World):
    """
    Helper for :func:`test_mosaik_remote()` that checks the "set_data()"
    RPC.
    """
    await channel.send(["set_data", [{"src": {"X.2": {"val": 23}}}], {}])
    compiled = world._async_world.compile()
    world._async_world._sims = compiled
    assert compiled["X"].inputs_from_set_data == {
        "2": {"val": {"src": 23}},
    }

    await channel.send(["set_data", [{"src": {"X.2": {"val": 42}}}], {}])
    assert compiled["X"].inputs_from_set_data == {
        "2": {"val": {"src": 42}},
    }


async def _rpc_get_data_err1(channel: Channel, world: World):
    """
    Required simulator not connected to us.
    """
    try:
        await channel.send(["get_data", [{"Z.2": []}], {}])
    except mosaik_api_v3.connection.RemoteException as exception:
        if exception.remote_type == "ScenarioError":
            raise ScenarioError


async def _rpc_get_data_err2(channel: Channel, world: World):
    """
    Async-requests flag not set for connection.
    """
    try:
        await channel.send(["get_data", [{"Y.2": []}], {}])
    except mosaik_api_v3.connection.RemoteException as exception:
        if exception.remote_type == "ScenarioError":
            raise ScenarioError


async def _rpc_set_data_err1(channel: Channel, world: World):
    """
    Required simulator not connected to us.
    """
    await channel.send(["set_data", [{"src": {"Z.2": {"val": 42}}}], {}])


async def _rpc_set_data_err2(channel: Channel, world: World):
    """
    Async-requests flag not set for connection.
    """
    await channel.send(["set_data", [{"src": {"Y.2": {"val": 42}}}], {}])


@pytest.mark.parametrize(
    ("rpc", "err"),
    [
        (_rpc_get_progress, None),
        (_rpc_get_related_entities, None),
        (_rpc_get_data, None),
        (_rpc_set_data, None),
        (_rpc_get_data_err1, ScenarioError),
        (_rpc_get_data_err2, ScenarioError),
        (_rpc_set_data_err1, RemoteException),
        (_rpc_set_data_err2, RemoteException),
    ],
)
def test_mosaik_remote(
    rpc: Callable[[Channel, World], Coroutine[Any, Any, None]],
    err: Type[Exception],
):
    world = scenario.World({})
    world.use_cache = True

    try:
        edges = [(0, 1), (0, 2), (1, 2), (2, 3)]
        edges = [("X.%s" % x, "X.%s" % y) for x, y in edges]
        world.entity_graph.add_edges_from(edges)
        for node in world.entity_graph:
            world.entity_graph.add_node(node, sim="ExampleSim", type="A")
        world.sim_progress = 23

        async def simulator(host: str, port: int):
            reader, writer = await asyncio.open_connection(host, port)
            channel = mosaik_api_v3.connection.Channel(reader, writer)
            try:
                await rpc(channel, world)
            finally:
                await channel.close()

        async def greeter(channel_future: asyncio.Future[Channel]):
            channel = await channel_future
            proxy_x = proxies.RemoteProxy(channel, simmanager.MosaikRemote(world, "X"))
            proxy_x._meta = {"type": "time-based", "models": {}}
            sim_x = simmanager.SimRunner("X", proxy_x, None)
            sim_x.successors[sim_x] = TieredDuration(0)
            sim_x.successors_to_wait_for[sim_x] = TieredDuration(0)
            sim_x.last_step = TieredTime(1)
            sim_x.current_step = TieredTime(0)
            sim_x.is_in_step = True
            sim_x.outputs = {1: {"2": {"attr": "val"}}}
            world._async_world._sims["X"] = sim_x

            class DummyProxy:
                @property
                def meta(self):
                    return {"type": "time-based", "models": {}}

                async def stop(self):
                    pass

            sim_y = simmanager.SimRunner("Y", DummyProxy(), None)
            world._async_world._sims["Y"] = sim_y
            sim_z = simmanager.SimRunner("Z", DummyProxy(), None)
            world._async_world._sims["Z"] = sim_z

            sim_x.successors[sim_y] = TieredDuration(0)

        async def run():
            channel_future: asyncio.Future[Channel] = asyncio.Future()

            async def on_connect(r: asyncio.StreamReader, w: asyncio.StreamWriter):
                channel_future.set_result(Channel(r, w))

            server = await asyncio.start_server(on_connect, "127.0.0.1")
            try:
                actual_addr = server.sockets[0].getsockname()
                sim_exc, greeter_exc = await asyncio.gather(
                    simulator(*actual_addr),
                    greeter(channel_future),
                    return_exceptions=True,
                )
            finally:
                server.close()
            assert greeter_exc is None
            if sim_exc:
                raise sim_exc

        if err:
            with pytest.raises(err):
                world.loop.run_until_complete(run())
        else:
            world.loop.run_until_complete(run())

    finally:
        world.shutdown()


def test_timed_input_buffer():
    """Test TimedInputBuffer, especially if a lower value is added at
    the same time for the same connection.
    """
    buffer = simmanager.TimedInputBuffer()
    buffer.add(1, "src_sid", "src_eid", "dest_eid", "dest_var", 2)
    buffer.add(1, "src_sid", "src_eid", "dest_eid", "dest_var", 1)
    buffer.add(2, "src_sid", "src_eid", "dest_eid", "dest_var", 0)
    input_dict = buffer.get_input({}, 0)
    assert input_dict == {}
    input_dict = buffer.get_input({}, 1)
    assert input_dict == {"dest_eid": {"dest_var": {"src_sid.src_eid": 1}}}


def test_global_time_resolution(world: World):
    # Default time resolution set to 1.0
    simulator = world.start("SimulatorMock")
    assert simulator._proxy.sim.time_resolution == 1.0

    # Set global time resolution to 60.0
    world._async_world.time_resolution = 60.0
    simulator_2 = world.start("SimulatorMock")
    assert simulator_2._proxy.sim.time_resolution == 60.0


def test_non_serializable_outputs_error(world: World):
    src_sim = world.start("FixedOutputSim")
    src_entity = src_sim.Entity(outputs={0: object()})
    dest_sim = world.start("ExampleSimB")
    dest_entity = dest_sim.B(init_val=0)
    world.connect(src_entity, dest_entity, ("out", "val_in"))
    with pytest.raises(NonSerializableOutputsError):
        world.run(until=1)


def test_repeated_entity_ids(world: World):
    """A cls:`DuplicateEntityIdError` should be raised if a simulator
    creates multiple entities with the same entity ID. (Otherwise,
    values for those entities get mixed up during the simulation.)"""
    # EchoSim always uses the entity ID "Echo"
    echo_sim = world.start("EchoSim")
    echo_sim.A()
    with pytest.raises(DuplicateEntityIdError) as exc_info:
        echo_sim.A()
    assert exc_info.value.simulator == "EchoSim-0"
    assert exc_info.value.entity_id == "Echo"
