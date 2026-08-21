from __future__ import annotations

import asyncio
from typing import Any, cast

import pytest
from loguru import logger
from mosaik_api_v3 import MosaikProxy
from mosaik_api_v3.connection import Channel, EndOfRequests

from mosaik.exceptions import ConnectionClosedError
from mosaik.proxies import LocalProxy, RemoteProxy
from tests.simulators.simulator_mock import SimulatorMock


class MosaikRemoteMock(MosaikProxy):
    def __init__(self, sid: str):
        self.sid = sid

    async def get_progress(self) -> float:
        return 0.5

    async def get_related_entities(self, entities: Any = None) -> dict[str, Any]:
        return {}

    async def get_data(self, attrs: Any) -> dict[str, Any]:
        return {}

    async def set_data(self, data: Any) -> None:
        pass

    async def set_event(self, event_time: Any) -> None:
        pass


class ChannelMock:
    _name = "Trace"

    def __init__(self, request: Any = None):
        self._closed = asyncio.Event()
        self._request = request

    async def next_request(self) -> Any:
        if self._request is not None:
            request = self._request
            self._request = None
            return request
        await self._closed.wait()
        raise EndOfRequests()

    async def send(self, request: Any) -> Any:
        if request[0] == "step":
            return 2
        return None

    async def close(self) -> None:
        self._closed.set()


class RequestMock:
    content = ("get_progress", (), {})

    def __init__(self):
        self.result = asyncio.Future()

    async def set_result(self, result: Any) -> None:
        self.result.set_result(result)

    async def set_exception(self, exception: Exception) -> None:
        self.result.set_exception(exception)


class FailingSimulator(SimulatorMock):
    def step(self, time: Any, inputs: Any, max_advance: Any) -> Any:
        raise RuntimeError("step failed")


class DisconnectedChannel(ChannelMock):
    async def send(self, request: Any) -> Any:
        raise asyncio.IncompleteReadError(b"", 1)


@pytest.fixture
def trace_records():
    handler_ids = []

    def capture(namespace: str):
        records = []
        handler_ids.append(
            logger.add(
                lambda message: records.append(message.record),
                level="TRACE",
                filter=lambda record: (
                    record["extra"].get("simulator", "").startswith(namespace)
                ),
            )
        )
        return records

    logger.disable("mosaik")
    yield capture
    for handler_id in handler_ids:
        logger.remove(handler_id)
    logger.disable("mosaik")


@pytest.mark.asyncio
async def test_local_proxy_traces_calls_in_both_directions(trace_records):
    records = trace_records("sim.local.Trace")
    logger.enable("mosaik")
    proxy = LocalProxy(SimulatorMock(), MosaikRemoteMock("Trace"))
    other_proxy = LocalProxy(SimulatorMock(), MosaikRemoteMock("Other"))

    await proxy.init("Trace", time_resolution=1.0)
    await other_proxy.init("Other", time_resolution=1.0)
    assert await proxy.sim.mosaik.get_progress() == 0.5
    await proxy.stop()
    await other_proxy.stop()

    assert {record["extra"]["simulator"] for record in records} == {"sim.local.Trace"}
    messages = [record["message"] for record in records]
    assert "mosaik -> simulator: init('Trace', time_resolution=1.0)" in messages
    assert any("simulator -> mosaik: init returned" in message for message in messages)
    assert "simulator -> mosaik: get_progress()" in messages
    assert "mosaik -> simulator: get_progress returned 0.5" in messages
    assert "mosaik -> simulator: finalize()" in messages


@pytest.mark.asyncio
async def test_remote_proxy_uses_remote_namespace(trace_records):
    records = trace_records("sim.remote.Trace")
    logger.enable("mosaik")
    request = RequestMock()
    channel = ChannelMock(request)
    proxy = RemoteProxy(cast(Channel, channel), cast(Any, MosaikRemoteMock("Trace")))

    assert await proxy.send(["step", [1, {}, 2], {}]) == 2
    assert await request.result == 0.5
    await proxy.stop()

    assert {record["extra"]["simulator"] for record in records} == {"sim.remote.Trace"}
    messages = [record["message"] for record in records]
    assert "mosaik -> simulator: step(1, {}, 2)" in messages
    assert "simulator -> mosaik: step returned 2" in messages
    assert "simulator -> mosaik: get_progress()" in messages


@pytest.mark.asyncio
async def test_simulator_traces_are_disabled_by_default(trace_records):
    records = trace_records("sim")
    proxy = LocalProxy(SimulatorMock(), MosaikRemoteMock("Trace"))

    await proxy.send(("step", (1, {}, 2), {}))

    assert records == []


@pytest.mark.asyncio
async def test_simulator_exceptions_are_traced_and_reraised(trace_records):
    records = trace_records("sim.local.Trace")
    logger.enable("mosaik")
    proxy = LocalProxy(FailingSimulator(), MosaikRemoteMock("Trace"))

    with pytest.raises(RuntimeError, match="step failed"):
        await proxy.send(("step", (1, {}, 2), {}))

    assert any(
        record["message"]
        == "simulator -> mosaik: step raised RuntimeError('step failed')"
        for record in records
    )


@pytest.mark.asyncio
async def test_remote_disconnect_is_not_reported_as_simulator_exception(trace_records):
    records = trace_records("sim.remote.Trace")
    logger.enable("mosaik")
    channel = DisconnectedChannel()
    proxy = RemoteProxy(cast(Channel, channel), cast(Any, MosaikRemoteMock("Trace")))

    with pytest.raises(ConnectionClosedError) as exc_info:
        await proxy.send(["step", [1, {}, 2], {}])

    assert isinstance(exc_info.value.__cause__, asyncio.IncompleteReadError)
    assert not any("raised" in record["message"] for record in records)
    await channel.close()
    await proxy._reader_task
