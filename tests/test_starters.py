import asyncio
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import cast

import mosaik_api_v3
import pytest
from example_sim.mosaik import ExampleSim

from mosaik import adapters
from mosaik.async_scenario import (
    MosaikConfig,
    MosaikConfigTotal,
    StarterConfig,
    base_config,
)
from mosaik.exceptions import ScenarioError, SimulationError
from mosaik.proxies import BaseProxy, LocalProxy
from mosaik.simmanager import MosaikRemote
from mosaik.starters import (
    CmdStarter,
    ConnectStarter,
    PythonStarter,
    Starter,
    get_starter_from_starter_config,
)
from tests.test_simmanager import SIM_CONFIG, VENV


@dataclass
class MockRemote:
    sid: str


DUMMY_REMOTE = cast(MosaikRemote, MockRemote("Spam"))
"""A remote for use in cases where no actual ``MosaikRemote`` is needed.
"""


async def start_starter(starter: Starter, config: MosaikConfig = {}) -> BaseProxy:
    full_config: MosaikConfigTotal = {**base_config, **config}
    proxy = await starter.start("Spam", DUMMY_REMOTE, full_config)
    return proxy


def test_get_starter():
    """Test that `get_starter_from_starter_config` creates the right
    type of starter.
    """

    starter = get_starter_from_starter_config(SIM_CONFIG["ExampleSimA"])
    assert isinstance(starter, PythonStarter)

    starter = get_starter_from_starter_config(SIM_CONFIG["ExampleSimB"])
    assert isinstance(starter, CmdStarter)

    starter = get_starter_from_starter_config(SIM_CONFIG["ExampleSimC"])
    assert isinstance(starter, ConnectStarter)


@pytest.mark.asyncio
async def test_start_in_process():
    """Test starting an in-proc simulator."""
    starter = PythonStarter.from_sim_config_entry(SIM_CONFIG["ExampleSimA"])
    assert isinstance(starter, PythonStarter)
    proxy = await starter.start(
        "ExampleSim-0",
        DUMMY_REMOTE,
        base_config,
    )
    assert isinstance(proxy, LocalProxy)
    assert isinstance(proxy.sim, ExampleSim)


@pytest.mark.cmd_process
@pytest.mark.asyncio
async def test_start_external_process():
    """Test starting a simulator as external process."""
    starter = CmdStarter.from_sim_config_entry(SIM_CONFIG["ExampleSimB"])
    assert isinstance(starter, CmdStarter)
    proxy = await start_starter(starter)
    adapter = await adapters.init_and_get_adapter(
        proxy, "ExampleSim-0", {"time_resolution": 1.0}, 10.0
    )
    assert "api_version" in adapter.meta and "models" in adapter.meta
    await proxy.stop()


@pytest.mark.asyncio
async def test_start_proc_timeout_accept():
    with pytest.raises(SimulationError) as exc_info:
        starter = CmdStarter.from_sim_config_entry(SIM_CONFIG["Fail"])
        await start_starter(starter, {"start_timeout": 0.1})
    assert (
        exc_info.value.args[0] == 'Simulator "Spam" did not connect to mosaik in time.'
    )


@pytest.mark.asyncio
async def test_start_proc_no_port_conflict():
    mosaik_config: MosaikConfig = {
        "addr": ("0.0.0.0", None),
        "start_timeout": 0,
        "stop_timeout": 1,
    }
    exc_1, exc_2 = await asyncio.gather(
        start_starter(CmdStarter(f"{VENV}/python --version"), mosaik_config),
        start_starter(CmdStarter(f"{VENV}/python --version"), mosaik_config),
        return_exceptions=True,
    )
    # We should get `SimulationError`s here, not `OSError`s -- the
    # latter would indicate that we tried to open two servers on the
    # same port
    assert isinstance(exc_1, Exception)
    if not isinstance(exc_1, SimulationError):
        raise exc_1
    assert isinstance(exc_2, Exception)
    if not isinstance(exc_2, SimulationError):
        raise exc_2


@pytest.mark.cmd_process
@pytest.mark.asyncio
async def test_start_external_process_with_environment_variables(tmp_path: Path):
    """
    Assert that you can set environment variables for a new sub-process.
    """
    # Replace sim_config for this test:z
    print(tmp_path)
    starter = CmdStarter(
        "%(python)s -m simulator_mock %(addr)s",
        env={
            "PYTHONPATH": str(tmp_path),
        },
    )

    # Write the module "simulator_mock.py" to tmpdir:
    with (tmp_path / "simulator_mock.py").open("w") as f:
        f.write(
            """
import mosaik_api_v3


class SimulatorMock(mosaik_api_v3.Simulator):
    def __init__(self):
        super().__init__(meta={})


if __name__ == '__main__':
    mosaik_api_v3.start_simulation(SimulatorMock())
"""
        )
    proxy = await start_starter(starter)
    await proxy.stop()


@pytest.mark.asyncio
async def test_start_connect():
    """
    Test connecting to an already running simulator.
    """

    async def mock_sim_server(r: asyncio.StreamReader, w: asyncio.StreamWriter):
        channel = mosaik_api_v3.connection.Channel(r, w)
        request = await channel.next_request()
        await request.set_result(ExampleSim().meta)
        await channel.next_request()
        await channel.close()

    server = await asyncio.start_server(mock_sim_server, "127.0.0.1", 5556)
    proxy = await start_starter(
        ConnectStarter.from_sim_config_entry(SIM_CONFIG["ExampleSimC"])
    )
    adapter = await adapters.init_and_get_adapter(
        proxy,
        "Spam",
        {"time_resolution": 1.0},
        start_timeout=base_config["start_timeout"],
    )
    assert "api_version" in adapter.meta and "models" in adapter.meta
    server.close()
    await adapter.stop()


@pytest.mark.asyncio
async def test_start_connect_timeout_init():
    """Simulator takes too long to respond to the init call."""

    async def mock_sim_server(r: asyncio.StreamReader, w: asyncio.StreamWriter):
        await mosaik_api_v3.connection.decode(r)
        await asyncio.sleep(0.11)
        w.close()
        await w.wait_closed()
        print("Writer closed")

    async with await asyncio.start_server(mock_sim_server, "127.0.0.1", 5556):
        proxy = await start_starter(
            ConnectStarter("127.0.0.1", 5556),
            {"start_timeout": 0.1},
        )
        with pytest.raises(SystemExit) as exc_info:
            await adapters.init_and_get_adapter(
                proxy,
                "Spam",
                {"time_resolution": 1.0},
                start_timeout=0.1,
            )
        assert (
            'Simulator "Spam" did not reply to the init() call in time.'
            == exc_info.value.args[0]
        )

        await asyncio.sleep(0.1)
        await proxy.stop()


@pytest.mark.asyncio
async def test_start_connect_stop_timeout():
    """
    Test connecting to an already running simulator.

    When asked to stop, the simulator times out.
    """

    async def mock_sim_server(r: asyncio.StreamReader, w: asyncio.StreamWriter):
        channel = mosaik_api_v3.connection.Channel(r, w)
        request = await channel.next_request()
        await request.set_result(ExampleSim().meta)
        await channel.next_request()  # Wait for stop message
        await channel.close()

    server = await asyncio.start_server(mock_sim_server, "127.0.0.1", 5556)

    proxy = await start_starter(
        ConnectStarter.from_sim_config_entry(SIM_CONFIG["ExampleSimC"])
    )
    adapter = await adapters.init_and_get_adapter(
        proxy,
        "Spam",
        {"time_resolution": 1.0},
        start_timeout=base_config["start_timeout"],
    )
    assert "api_version" in adapter.meta and "models" in adapter.meta
    await adapter.stop()
    server.close()


@pytest.mark.parametrize(
    ("starter_config", "err_msg"),
    [
        ({}, "does not match any known starter"),
        (
            {"python": "eggs"},
            'malformed import string for python starter, expected "module:Class"',
        ),
        ({"python": "eggs:Bacon"}, "could not import module `eggs`"),
        (
            {"python": "example_sim:Bacon"},
            "class `Bacon` not found in module `example_sim`",
        ),
        ({"cmd": "foo"}, "No such file or directory: 'foo'"),
        ({"cmd": "python", "cwd": "bar"}, "No such file or directory: 'bar'"),
        ({"connect": "eggs"}, 'Could not parse address "eggs"'),
    ],
)
@pytest.mark.asyncio
async def test_start_user_error(starter_config: StarterConfig, err_msg: str):
    """
    Test failure at starting an in-proc simulator.
    """
    with pytest.raises(ScenarioError) as exc_info:
        starter = get_starter_from_starter_config(starter_config)
        proxy = await start_starter(starter)
        await proxy.stop()
    if sys.platform != "win32":  # pragma: no cover
        # Windows has strange error messages which we do not want to
        # check :(
        assert err_msg in str(exc_info.value)


@pytest.mark.asyncio
async def test_start_sim_error():
    """
    Test connection failures of external processes.
    """
    starter = ConnectStarter(host="foo", port=1234)
    with pytest.raises(SimulationError) as exc_info:
        await start_starter(starter)

    assert (
        'Simulator "Spam" could not be started: Could not connect to '
        '"foo:1234"' == exc_info.value.args[0]
    )


@pytest.mark.asyncio
async def test_start_init_error():
    """
    Test simulator crashing during init().
    """
    starter = CmdStarter(f"{VENV}/pyexamplesim %(addr)s")
    with pytest.raises(SystemExit) as exc_info:
        base_proxy = await start_starter(starter)
        await adapters.init_and_get_adapter(
            base_proxy,
            "Spam",
            {"foo": 3},
            start_timeout=1.0,
        )
    assert (
        'Simulator "Spam" closed its connection during the init() call.'
        == exc_info.value.args[0]
    )
