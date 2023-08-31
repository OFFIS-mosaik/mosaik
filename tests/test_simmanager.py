import asyncio
import pytest
import sys

from example_sim.mosaik import ExampleSim
from mosaik_api_v3 import __api_version__ as api_version

from mosaik import scenario
from mosaik import simmanager
from mosaik import proxies
from mosaik.exceptions import ScenarioError, SimulationError
import mosaik
from mosaik.proxies import APIProxy, LocalProxy, RemoteException

sim_config = {
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
    "ExampleSimD": {},
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
        meta = {"api_version": api_version, "models": {}}

        @classmethod
        async def init(cls, *args, **kwargs):
            return cls.meta

    async def start(*args, **kwargs):
        return Proxy

    s = simmanager.StarterCollection()
    monkeypatch.setitem(s, "python", start)
    monkeypatch.setitem(s, "cmd", start)
    monkeypatch.setitem(s, "connect", start)

    ret = world.loop.run_until_complete(
        simmanager.start(world, "ExampleSimA", "0", 1.0, {})
    )
    assert ret.proxy == Proxy

    # The api_version has to be re-initialized, because it is changed in
    # simmanager.start()
    Proxy.meta["api_version"] = api_version
    ret = world.loop.run_until_complete(
        simmanager.start(world, "ExampleSimB", "0", 1.0, {})
    )
    assert ret.proxy == Proxy

    # The api_version has to re-initialized
    Proxy.meta["api_version"] = api_version
    ret = world.loop.run_until_complete(
        simmanager.start(world, "ExampleSimC", "0", 1.0, {})
    )
    assert ret.proxy == Proxy


def test_start_wrong_api_version(world, monkeypatch):
    """
    An exception should be raised if the simulator uses an unsupported
    API version."""
    monkeypatch.setattr(mosaik.proxies, "API_MAJOR", 1000)
    monkeypatch.setattr(mosaik.proxies, "API_MINOR", 5)
    with pytest.raises(ScenarioError) as exc_info:
        world.loop.run_until_complete(
            simmanager.start(world, "ExampleSimA", "0", 1.0, {})
        )

    assert str(exc_info.value) in (
        f'Simulator "ExampleSimA" could not be started: Invalid version '
        '"{api_version}": Version must be between 1000.0 and 1000.5'
    )


def test_start_in_process(world):
    """
    Test starting an in-proc simulator."""
    sp = world.loop.run_until_complete(
        simmanager.start(world, "ExampleSimA", "ExampleSim-0", 1.0, {"step_size": 2})
    )
    assert sp.sid == "ExampleSim-0"
    assert sp.type
    assert isinstance(sp.proxy, LocalProxy)
    assert isinstance(sp.proxy.sim, ExampleSim)
    assert sp.proxy.sim.step_size == 2


@pytest.mark.cmd_process
def test_start_external_process(world):
    """
    Test starting a simulator as external process."""
    sp = world.loop.run_until_complete(
        simmanager.start(world, "ExampleSimB", "ExampleSim-0", 1.0, {})
    )
    assert sp.sid == "ExampleSim-0"
    assert "api_version" in sp.proxy.meta and "models" in sp.proxy.meta
    world.loop.run_until_complete(sp.stop())


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
        await read_message(reader)
        writer.write(proxies.encode([1, 0, ExampleSim().meta]))
        await writer.drain()
        await read_message(reader)
        writer.close()

    server = world.loop.run_until_complete(
        asyncio.start_server(mock_sim_server, "127.0.0.1", 5556)
    )
    sim = world.loop.run_until_complete(
        simmanager.start(world, "ExampleSimC", "ExampleSim-0", 1.0, {})
    )
    assert sim.sid == "ExampleSim-0"
    assert "api_version" in sim.proxy.meta and "models" in sim.proxy.meta
    server.close()
    world.loop.run_until_complete(sim.stop())


def test_start_connect_timeout_init(world, caplog):
    """
    Test connecting to an already running simulator.
    """
    world.config["start_timeout"] = 0.1

    async def mock_sim_server(reader, writer):
        await read_message(reader)
        import time

        time.sleep(0.15)
        writer.close()

    server = world.loop.run_until_complete(
        asyncio.start_server(mock_sim_server, "127.0.0.1", 5556)
    )
    with pytest.raises(SystemExit) as exc_info:
        world.loop.run_until_complete(
            simmanager.start(world, "ExampleSimC", "", 1.0, {})
        )
    assert (
        'Simulator "ExampleSimC" did not reply to the init() call in time.'
        == exc_info.value.args[0]
    )
    server.close()


def test_start_connect_stop_timeout(world):
    """
    Test connecting to an already running simulator.

    When asked to stop, the simulator times out.
    """

    async def mock_sim_server(reader, writer):
        await read_message(reader)
        writer.write(proxies.encode([1, 0, ExampleSim().meta]))
        await writer.drain()
        await read_message(reader)  # Wait for stop message
        writer.close()

    server = world.loop.run_until_complete(
        asyncio.start_server(mock_sim_server, "127.0.0.1", 5556)
    )

    sim = world.loop.run_until_complete(
        simmanager.start(world, "ExampleSimC", "ExampleSim-0", 1.0, {})
    )
    sim._stop_timeout = 0.01
    assert sim.sid == "ExampleSim-0"
    assert "api_version" in sim.proxy.meta and "models" in sim.proxy.meta
    world.loop.run_until_complete(sim.stop())
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


@pytest.mark.parametrize(
    ["version", "result"],
    [
        ("3.0", (3, 0)),
        (3.0, (3, 0)),
    ],
)
def test_validate_api_version(version, result):
    assert proxies.validate_api_version(version) == result


@pytest.mark.parametrize(
    "version",
    [
        "1",
        "1.2",
        "2",
        "2,1",
        2,
        2.11,
        "3.99",
        "4.1",
        "3a",
    ],
)
def test_validate_api_version_wrong_version(version):
    with pytest.raises(ScenarioError) as se:
        proxies.validate_api_version(version)
    assert "Version" in str(se.value)


def test_sim_proxy_illegal_model_names(world):
    with pytest.raises(ScenarioError):
        world.start("MetaMock", meta={"models": {"step": {}}})


def test_sim_proxy_illegal_extra_methods(world):
    with pytest.raises(ScenarioError):
        world.start("MetaMock", meta={"models": {"A": {}}, "extra_methods": ["step"]})
    with pytest.raises(ScenarioError):
        world.start("MetaMock", meta={"models": {"A": {}}, "extra_methods": ["A"]})


def test_sim_proxy_stop_impl(world):
    class Test(APIProxy):
        def stop(self):
            raise NotImplementedError()

        async def _send(self, *args, **kwargs):
            raise NotImplementedError()

        meta = {"models": {}}

    sim = simmanager.SimRunner("spam", "id", world, Test(None))
    with pytest.raises(NotImplementedError):
        world.loop.run_until_complete(sim.stop())


def test_local_process(world):
    es = ExampleSim()
    proxy = LocalProxy(None, es)
    world.loop.run_until_complete(proxy.init("ExampleSim-0", time_resolution=1.0))
    sim = simmanager.SimRunner("ExampleSim", "ExampleSim-0", world, proxy)
    assert sim.name == "ExampleSim"
    assert sim.sid == "ExampleSim-0"
    assert sim.proxy.sim is es
    assert sim.last_step == -1
    assert sim.next_steps == [0]


def test_local_process_finalized(world):
    """
    Test that ``finalize()`` is called for local processes (issue #23).
    """
    simulator = world.start("SimulatorMock")
    assert simulator._sim.proxy.sim.finalized is False
    world.run(until=1)
    assert simulator._sim.proxy.sim.finalized is True


async def _rpc_request(reader, writer, func, *args, **kwargs):
    writer.write(proxies.encode([proxies.REQUEST, 0, [func, args, kwargs]]))
    await writer.drain()
    msg_type, _, result = await proxies.decode(reader)
    if msg_type == proxies.SUCCESS:
        return result
    else:
        raise RemoteException(result)


async def _rpc_get_progress(reader, writer, world):
    """
    Helper for :func:`test_mosaik_remote()` that checks the "get_progress()"
    RPC.
    """
    progress = await _rpc_request(reader, writer, "get_progress")
    assert progress == 23


async def _rpc_get_related_entities(reader, writer, world):
    """
    Helper for :func:`test_mosaik_remote()` that checks the
    "get_related_entities()" RPC.
    """
    # No param yields complete entity graph
    entities = await _rpc_request(reader, writer, "get_related_entities")
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
    entities = await _rpc_request(reader, writer, "get_related_entities", "X.0")
    assert entities == {
        "X.1": {"sim": "ExampleSim", "type": "A"},
        "X.2": {"sim": "ExampleSim", "type": "A"},
    }

    # List of strings yields dicts with related entities grouped by input ids
    entities = await _rpc_request(
        reader, writer, "get_related_entities", ["X.1", "X.2"]
    )
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


async def _rpc_get_data(reader, writer, world):
    """
    Helper for :func:`test_mosaik_remote()` that checks the "get_data()"
    RPC.
    """
    data = await _rpc_request(reader, writer, "get_data", {"X.2": ["attr"]})
    assert data == {"X.2": {"attr": "val"}}


async def _rpc_set_data(reader, writer, world):
    """
    Helper for :func:`test_mosaik_remote()` that checks the "set_data()"
    RPC.
    """
    await _rpc_request(reader, writer, "set_data", {"src": {"X.2": {"val": 23}}})
    assert world.sims["X"].input_buffer == {
        "2": {"val": {"src": 23}},
    }

    await _rpc_request(reader, writer, "set_data", {"src": {"X.2": {"val": 42}}})
    assert world.sims["X"].input_buffer == {
        "2": {"val": {"src": 42}},
    }


async def _rpc_get_data_err1(reader, writer, world):
    """
    Required simulator not connected to us.
    """
    try:
        await _rpc_request(reader, writer, "get_data", {"Z.2": []})
    except RemoteException as exception:
        if _remote_exception_type(exception) == "mosaik.exceptions.ScenarioError":
            raise ScenarioError


def _remote_exception_type(exception):
    return "mosaik.exceptions.ScenarioError"
    # TODO: Get remote_traceback back
    remote_exception_type = exception.remote_traceback.split("\n")[-2].split(":")[0]
    return remote_exception_type


async def _rpc_get_data_err2(reader, writer, world):
    """
    Async-requests flag not set for connection.
    """
    try:
        await _rpc_request(reader, writer, "get_data", {"Y.2": []})
    except RemoteException as exception:
        if _remote_exception_type(exception) == "mosaik.exceptions.ScenarioError":
            raise ScenarioError


async def _rpc_set_data_err1(reader, writer, world):
    """
    Required simulator not connected to us.
    """
    await _rpc_request(reader, writer, "set_data", {"src": {"Z.2": {"val": 42}}})


async def _rpc_set_data_err2(reader, writer, world):
    """
    Async-requests flag not set for connection.
    """
    await _rpc_request(reader, writer, "set_data", {"src": {"Y.2": {"val": 42}}})


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

    try:
        edges = [(0, 1), (0, 2), (1, 2), (2, 3)]
        edges = [("X.%s" % x, "X.%s" % y) for x, y in edges]
        world.df_graph.add_edge("X", "X", async_requests=True)
        world.df_graph.add_edge("Y", "X", async_requests=False)
        world.df_graph.add_node("Z")
        world.entity_graph.add_edges_from(edges)
        for node in world.entity_graph:
            world.entity_graph.add_node(node, sim="ExampleSim", type="A")
        world.sim_progress = 23
        world._df_cache = {
            1: {
                "X": {"2": {"attr": "val"}},
            },
        }

        async def simulator():
            reader, writer = await asyncio.open_connection("127.0.0.1", 5555)
            try:
                await rpc(reader, writer, world)
            finally:
                writer.close()

        async def greeter():
            reader, writer = await world.incoming_connections_queue.get()
            proxy = proxies.RemoteProxy(
                simmanager.MosaikRemote(world, "X"), reader, writer
            )
            proxy.meta = {"models": {}}
            sim = simmanager.SimRunner("X", "X", world, proxy)
            sim.last_step = 1
            sim.is_in_step = True
            world.sims["X"] = sim

        async def run():
            sim_exc, greeter_exc = await asyncio.gather(
                simulator(),
                greeter(),
                return_exceptions=True,
            )
            assert greeter_exc == None
            if sim_exc:
                raise sim_exc
            
        if err:
            with pytest.raises(err):
                world.loop.run_until_complete(run())
        else:
            world.loop.run_until_complete(run())

    finally:
        world.server.close()


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
    assert simulator._sim._world.time_resolution == 1.0

    # Set global time resolution to 60.0
    world.time_resolution = 60.0
    simulator_2 = world.start("SimulatorMock")
    assert simulator_2._sim._world.time_resolution == 60.0
