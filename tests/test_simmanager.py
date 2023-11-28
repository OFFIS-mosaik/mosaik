import asyncio
from asyncio import StreamReader, StreamWriter
from loguru import logger
import pytest
import sys
import time
from typing import Optional

from example_sim.mosaik import ExampleSim
from mosaik_api_v3 import __api_version__ as api_version
import mosaik_api_v3.connection
from mosaik_api_v3.connection import RemoteException

from mosaik import proxies, scenario, simmanager, World
from mosaik.dense_time import DenseTime
from mosaik.exceptions import ScenarioError, SimulationError
from mosaik.proxies import BaseProxy, LocalProxy


sim_config: scenario.SimConfig = {
    "ExampleSimA": {
        "python": "example_sim.mosaik:ExampleSim",
    },
    "ExampleSimB": {
        "cmd": "pyexamplesim %(addr)s",
        "cwd": ".",
    },
    "ExampleSimC": {
        "connect": "127.0.0.1:5556",
    },
    "ExampleSimD": {},  # type: ignore  # this is used for testing for this error
    "Fail": {
        "cmd": 'python -c "import time; time.sleep(0.2)"',
    },
    "SimulatorMock": {
        "python": "tests.mocks.simulator_mock:SimulatorMock",
    },
    "MetaMock": {
        "python": "tests.mocks.meta_mock:MetaMock",
    },
}


@pytest.fixture(name="world")
def world_fixture():
    world = scenario.World(sim_config)
    yield world
    world.shutdown()


def test_start(world, monkeypatch):
    """
    Test if start() dispatches to the correct start functions.
    """

    class Proxy(object):
        @classmethod
        async def init(cls, *args, **kwargs):
            return list(map(int, api_version.split('.')))
        
        @classmethod
        async def send(cls, request):
            return None

    async def start(*args, **kwargs):
        return Proxy

    s = simmanager.StarterCollection()
    monkeypatch.setitem(s, "python", start)
    monkeypatch.setitem(s, "cmd", start)
    monkeypatch.setitem(s, "connect", start)

    ret = world.loop.run_until_complete(
        simmanager.start(world, "ExampleSimA", "0", 1.0, {})
    )
    assert ret == Proxy

    # The api_version has to be re-initialized, because it is changed in
    # simmanager.start()
    ret = world.loop.run_until_complete(
        simmanager.start(world, "ExampleSimB", "0", 1.0, {})
    )
    assert ret == Proxy

    # The api_version has to re-initialized
    ret = world.loop.run_until_complete(
        simmanager.start(world, "ExampleSimC", "0", 1.0, {})
    )
    assert ret == Proxy


def test_start_wrong_api_version(world, monkeypatch):
    """
    An exception should be raised if the simulator uses an unsupported
    API version."""
    with pytest.raises(ScenarioError) as exc_info:
        world.loop.run_until_complete(
            simmanager.start(world, "MetaMock", "MetaMock-0", 1.0, {"meta": {"api_version": "1000.0"}})
        )

    assert str(exc_info.value) == (
        "There was an error during the initialization of MetaMock-0: The API version "
        "(1000.0) is too new for this version of mosaik. Maybe a newer version of the "
        "mosaik package is available to be used in your scenario?"
    )


def test_start_in_process(world):
    """
    Test starting an in-proc simulator."""
    connection = world.loop.run_until_complete(
        simmanager.start(world, "ExampleSimA", "ExampleSim-0", 1.0, {"step_size": 2})
    )
    assert isinstance(connection, LocalProxy)
    assert isinstance(connection.sim, ExampleSim)
    assert connection.sim.step_size == 2


@pytest.mark.cmd_process
def test_start_external_process(world):
    """
    Test starting a simulator as external process."""
    proxy = world.loop.run_until_complete(
        simmanager.start(world, "ExampleSimB", "ExampleSim-0", 1.0, {})
    )
    assert "api_version" in proxy.meta and "models" in proxy.meta
    world.loop.run_until_complete(proxy.stop())


def test_start_proc_timeout_accept(world, caplog):
    world.config["start_timeout"] = 0.1
    with pytest.raises(SimulationError) as exc_info:
        world.loop.run_until_complete(simmanager.start(world, "Fail", "", 1.0, {}))
    assert (
        exc_info.value.args[0] == 'Simulator "Fail" did not connect to mosaik in time.'
    )


@pytest.mark.cmd_process
def test_start_external_process_with_environment_variables(world, tmpdir):
    """
    Assert that you can set environment variables for a new sub-process.
    """
    # Replace sim_config for this test:
    print(tmpdir.strpath)
    world.sim_config = {
        "SimulatorMockTmp": {
            "cmd": "%(python)s -m simulator_mock %(addr)s",
            "env": {
                "PYTHONPATH": tmpdir.strpath,
            },
        }
    }

    # Write the module "simulator_mock.py" to tmpdir:
    tmpdir.join("simulator_mock.py").write(
        """
import mosaik_api_v3


class SimulatorMock(mosaik_api_v3.Simulator):
    def __init__(self):
        super().__init__(meta={})


if __name__ == '__main__':
    mosaik_api_v3.start_simulation(SimulatorMock())
"""
    )
    sim = world.start("SimulatorMockTmp")


async def read_message(reader: asyncio.StreamReader):
    length = int.from_bytes(await reader.readexactly(4), "big")
    return await reader.readexactly(length)


def test_start_connect(world: scenario.World):
    """
    Test connecting to an already running simulator.
    """

    async def mock_sim_server(reader, writer):
        channel = mosaik_api_v3.connection.Channel(reader, writer)
        request = await channel.next_request()
        await request.set_result(ExampleSim().meta)
        await channel.next_request()
        await channel.close()

    server = world.loop.run_until_complete(
        asyncio.start_server(mock_sim_server, "127.0.0.1", 5556)
    )
    simC = world.start("ExampleSimC")
    world.shutdown()
    assert "api_version" in simC.meta and "models" in simC.meta
    server.close()


def test_start_connect_timeout_init(world: World, caplog):
    """Simulator takes too long to respond to the init call.
    """
    world.config["start_timeout"] = 0.1

    async def mock_sim_server(reader: StreamReader, writer: StreamWriter):
        await read_message(reader)
        await asyncio.sleep(0.11)
        writer.close()
        await writer.wait_closed()
        print("Writer closed")

    server = world.loop.run_until_complete(
        asyncio.start_server(mock_sim_server, "127.0.0.1", 5556)
    )
    with pytest.raises(SystemExit) as exc_info:
        world.start("ExampleSimC")
    assert (
        'Simulator "ExampleSimC" did not reply to the init() call in time.'
        == exc_info.value.args[0]
    )

    world.loop.run_until_complete(asyncio.sleep(0.1))
    server.close()


def test_start_connect_stop_timeout(world: World):
    """
    Test connecting to an already running simulator.

    When asked to stop, the simulator times out.
    """

    async def mock_sim_server(reader: StreamReader, writer: StreamWriter):
        channel = mosaik_api_v3.connection.Channel(reader, writer)
        request = await channel.next_request()
        await request.set_result(ExampleSim().meta)
        await channel.next_request()  # Wait for stop message
        await channel.close()

    server = world.loop.run_until_complete(
        asyncio.start_server(mock_sim_server, "127.0.0.1", 5556)
    )

    sim = world.start("ExampleSimC")
    assert "api_version" in sim.meta and "models" in sim.meta
    world.shutdown()
    server.close()


@pytest.mark.parametrize(
    ("sim_config", "err_msg"),
    [
        ({}, "Not found in sim_config"),
        ({"spam": {}}, "Invalid configuration"),
        (
            {"spam": {"python": "eggs"}},
            'Malformed Python class name: Expected "module:Class" --> not enough '
            "values to unpack (expected 2, got 1)",
        ),
        (
            {"spam": {"python": "eggs:Bacon"}},
            "Could not import module: No module named 'eggs' --> No module named "
            "'eggs'",
        ),
        (
            {"spam": {"python": "example_sim:Bacon"}},
            "Class not found in module --> module 'example_sim' has no attribute "
            "'Bacon'",
        ),
        ({"spam": {"cmd": "foo"}}, "No such file or directory: 'foo'"),
        ({"spam": {"cmd": "python", "cwd": "bar"}}, "No such file or directory: 'bar'"),
        ({"spam": {"connect": "eggs"}}, 'Could not parse address "eggs"'),
    ],
)
def test_start_user_error(sim_config, err_msg):
    """
    Test failure at starting an in-proc simulator.
    """
    world = scenario.World(sim_config)
    try:
        with pytest.raises(ScenarioError) as exc_info:
            world.loop.run_until_complete(simmanager.start(world, "spam", "", 1.0, {}))
        if sys.platform != "win32":  # pragma: no cover
            # Windows has strange error messages which do not want to check :(
            assert str(exc_info.value) == (
                f'Simulator "spam" could not be started: {err_msg}'
            )
    finally:
        world.shutdown()


def test_start_sim_error(caplog):
    """
    Test connection failures of external processes.
    """
    world = scenario.World({"spam": {"connect": "foo:1234"}})
    try:
        with pytest.raises(SimulationError) as exc_info:
            world.loop.run_until_complete(
                simmanager.start(world, "spam", "", 1.0, {"foo": "bar"})
            )

        assert (
            'Simulator "spam" could not be started: Could not connect to '
            '"foo:1234"' == exc_info.value.args[0]
        )
    finally:
        world.shutdown()


def test_start_init_error(caplog):
    """
    Test simulator crashing during init().
    """
    world = scenario.World({"spam": {"cmd": "pyexamplesim %(addr)s"}})
    try:
        with pytest.raises(SystemExit) as exc_info:
            world.loop.run_until_complete(
                simmanager.start(world, "spam", "", 1.0, {"foo": 3})
            )
        assert (
            'Simulator "spam" closed its connection during the init() call.'
            == exc_info.value.args[0]
        )
    finally:
        world.shutdown()


def test_sim_proxy_illegal_model_names(world):
    with pytest.raises(ScenarioError):
        world.start("MetaMock", meta={"models": {"step": {}}})


def test_sim_proxy_illegal_extra_methods(world):
    with pytest.raises(ScenarioError):
        world.start("MetaMock", meta={"models": {"A": {}}, "extra_methods": ["step"]})
    with pytest.raises(ScenarioError):
        world.start("MetaMock", meta={"models": {"A": {}}, "extra_methods": ["A"]})


def test_sim_proxy_stop_impl(world):
    class Test(BaseProxy):
        def init(self):
            raise NotImplementedError()

        def stop(self):
            raise NotImplementedError()

        async def send(self, *args, **kwargs):
            raise NotImplementedError()

        meta = {"type": "time-based", "models": {}}

    sim = simmanager.SimRunner("id", Test())
    with pytest.raises(NotImplementedError):
        world.loop.run_until_complete(sim.stop())


def test_local_process(world):
    es = ExampleSim()
    proxy = LocalProxy(es, None)
    world.loop.run_until_complete(proxy.init("ExampleSim-0", time_resolution=1.0))
    sim = simmanager.SimRunner("ExampleSim-0", proxy)
    assert sim.sid == "ExampleSim-0"
    assert sim._proxy.sim is es
    assert sim.last_step == DenseTime(-1)
    assert sim.next_steps == [DenseTime(0)]


def test_local_process_finalized(world):
    """
    Test that ``finalize()`` is called for local processes (issue #23).
    """
    simulator = world.start("SimulatorMock")
    assert simulator._proxy.sim.finalized is False
    world.run(until=1)
    assert simulator._proxy.sim.finalized is True


async def _rpc_get_progress(channel, world):
    """ 
    Helper for :func:`test_mosaik_remote()` that checks the "get_progress()"
    RPC.
    """
    progress = await channel.send(["get_progress", [], {}])
    assert progress == 23


async def _rpc_get_related_entities(channel, world):
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

    # List of strings yields dicts with related entities grouped by input ids
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


async def _rpc_get_data(channel, world):
    """
    Helper for :func:`test_mosaik_remote()` that checks the "get_data()"
    RPC.
    """
    data = await channel.send(["get_data", [{"X.2": ["attr"]}], {}])
    assert data == {"X.2": {"attr": "val"}}


async def _rpc_set_data(channel, world: scenario.World):
    """
    Helper for :func:`test_mosaik_remote()` that checks the "set_data()"
    RPC.
    """
    await channel.send(["set_data", [{"src": {"X.2": {"val": 23}}}], {}])
    assert world.sims["X"].inputs_from_set_data == {
        "2": {"val": {"src": 23}},
    }

    await channel.send(["set_data", [{"src": {"X.2": {"val": 42}}}], {}])
    assert world.sims["X"].inputs_from_set_data == {
        "2": {"val": {"src": 42}},
    }


async def _rpc_get_data_err1(channel, world):
    """
    Required simulator not connected to us.
    """
    try:
        await channel.send(["get_data", [{"Z.2": []}], {}])
    except mosaik_api_v3.connection.RemoteException as exception:
        if exception.remote_type == "ScenarioError":
            raise ScenarioError


def _remote_exception_type(exception):
    return "mosaik.exceptions.ScenarioError"
    # TODO: Get remote_traceback back
    remote_exception_type = exception.remote_traceback.split("\n")[-2].split(":")[0]
    return remote_exception_type


async def _rpc_get_data_err2(channel, world):
    """
    Async-requests flag not set for connection.
    """
    try:
        await channel.send(["get_data", [{"Y.2": []}], {}])
    except mosaik_api_v3.connection.RemoteException as exception:
        if exception.remote_type == "ScenarioError":
            raise ScenarioError


async def _rpc_set_data_err1(channel, world):
    """
    Required simulator not connected to us.
    """
    await channel.send(["set_data", [{"src": {"Z.2": {"val": 42}}}], {}])


async def _rpc_set_data_err2(channel, world):
    """
    Async-requests flag not set for connection.
    """
    await channel.send(["set_data", [{"src": {"Y.2": {"val": 42}}}], {}])


@pytest.mark.skip()
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
def test_mosaik_remote(rpc, err):
    world = scenario.World({})
    world.use_cache = True

    try:
        edges = [(0, 1), (0, 2), (1, 2), (2, 3)]
        edges = [("X.%s" % x, "X.%s" % y) for x, y in edges]
        # world.df_graph.add_edge("X", "X", async_requests=True)
        # world.df_graph.add_edge("Y", "X", async_requests=False)
        # world.df_graph.add_node("Z")
        world.entity_graph.add_edges_from(edges)
        for node in world.entity_graph:
            world.entity_graph.add_node(node, sim="ExampleSim", type="A")
        world.sim_progress = 23

        async def simulator():
            reader, writer = await asyncio.open_connection("localhost", 5555)
            channel = mosaik_api_v3.connection.Channel(reader, writer)
            try:
                await rpc(channel, world)
            finally:
                await channel.close()

        async def greeter():
            channel = await world.incoming_connections_queue.get()
            proxy = proxies.RemoteProxy(channel, simmanager.MosaikRemote(world, "X"))
            proxy._meta = {"type": "time-based", "models": {}}
            sim = simmanager.SimRunner("X", proxy)
            sim.last_step = DenseTime(1)
            sim.current_step = DenseTime(0)
            sim.is_in_step = True
            world.sims["X"] = sim
            world.sims["X"].outputs = {1: {"2": {"attr": "val"}}}

        async def run():
            sim_exc, greeter_exc = await asyncio.gather(
                simulator(),
                greeter(),
                return_exceptions=True,
            )
            assert greeter_exc is None
            if sim_exc:
                raise sim_exc

        if err:
            with pytest.raises(err):
                world.loop.run_until_complete(run())
        else:
            world.loop.run_until_complete(run())

    finally:
        world.loop.run_until_complete(world.sims["X"].stop())
        world.server.close()
        world.loop.close()


def test_timed_input_buffer():
    """Test TimedInputBuffer, especially if a lower value is added at the same
    time for the same connection.
    """
    buffer = simmanager.TimedInputBuffer()
    buffer.add(1, "src_sid", "src_eid", "dest_eid", "dest_var", 2)
    buffer.add(1, "src_sid", "src_eid", "dest_eid", "dest_var", 1)
    buffer.add(2, "src_sid", "src_eid", "dest_eid", "dest_var", 0)
    input_dict = buffer.get_input({}, 0)
    assert input_dict == {}
    input_dict = buffer.get_input({}, 1)
    assert input_dict == {"dest_eid": {"dest_var": {"src_sid.src_eid": 1}}}


def test_global_time_resolution(world):
    # Default time resolution set to 1.0
    simulator = world.start("SimulatorMock")
    assert simulator._proxy.sim.time_resolution == 1.0

    # Set global time resolution to 60.0
    world.time_resolution = 60.0
    simulator_2 = world.start("SimulatorMock")
    assert simulator_2._proxy.sim.time_resolution == 60.0
