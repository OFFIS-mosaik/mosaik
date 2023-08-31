from __future__ import annotations

from abc import ABC, abstractmethod
import asyncio
from copy import deepcopy
from inspect import isgeneratorfunction
from itertools import count
from json import JSONEncoder, JSONDecoder
from typing import Any, Dict, Iterator, Optional, Tuple, TYPE_CHECKING, Union
from loguru import logger

import mosaik_api_v3
from mosaik import _version
from mosaik.exceptions import ScenarioError

if TYPE_CHECKING:
    from mosaik.simmanager import MosaikRemote
    from mosaik.scenario import Meta, SimId, OutputData, InputData

API_MAJOR = _version.VERSION_INFO[0]  # Current major version of the sim API
API_MINOR = _version.VERSION_INFO[1]  # Current minor version of the sim API
API_VERSION = '%s.%s' % (API_MAJOR, API_MINOR)  # Current version of the API


class APIProxy(ABC):
    """
    This is a proxy for a mosaik simulator that provides asynchronous access to its
    standard and extra methods.
    """

    _mosaik_remote: MosaikRemote
    _old_api: bool
    _api_compliant: bool
    meta: Meta

    def __init__(self, mosaik_remote: MosaikRemote):
        self._mosaik_remote = mosaik_remote
        self._old_api = False
        self._api_compliant = True

    async def init(self, sid, *, time_resolution: float, **kwargs) -> None:
        if self._api_compliant:
            kwargs["time_resolution"] = time_resolution

        meta: Meta = await self._send("init", (sid,), kwargs)
        meta = deepcopy(meta)

        if 'type' not in meta:
            self._old_api = True

        meta.setdefault("extra_methods", [])
        self._check_model_and_meth_names(sid, meta)
        for method_name in meta["extra_methods"]:
            self._add_extra_method(method_name)

        meta['api_version'] = validate_api_version(meta['api_version'])
        type_check(meta, sid, sid)
        meta = expand_meta(meta, sid)
        for props in meta['models'].values():
            props.setdefault('any_inputs', False)
        self.meta = meta
    
    def _add_extra_method(self, method_name):
        async def f(*args, **kwargs):
            return await self._send(method_name, args, kwargs)
        setattr(self, method_name, f)

    def _check_model_and_meth_names(self, sid: SimId, meta: Meta) -> None:
        """
        Check if there are any overlaps in model names and reserved API
        methods as well as in them and extra API methods.

        Raise a :exc:`~mosaik.exception.ScenarioError` if that's the case.
        """
        models = set(meta['models'])
        api_methods = set(["init", "get_data", "create", "step"])
        extra_methods = set(meta['extra_methods'])
        illegal_models = models & api_methods
        if illegal_models:
            raise ScenarioError(
                f'Simulator "{sid}" uses illegal model names: '
                f'{", ".join(illegal_models)}'
            )

        illegal_meths = (models | api_methods) & extra_methods
        if illegal_meths:
            raise ScenarioError(
                f'Simulator "{sid}" uses illegal extra method names: '
                f'{", ".join(illegal_meths)}'
            )

    async def create(self, num: int, model: str, **kwargs):
        return await self._send("create", (num, model), kwargs)

    async def setup_done(self) -> None:
        # setup_done() was added in API version 2.2
        if self.meta['api_version'] >= (2, 2):
            return await self._send("setup_done", (), {})

    async def step(
        self,
        time: int,
        inputs: InputData,
        max_advance: int
    ) -> Optional[int]:
        if self._api_compliant and not self._old_api:
            return await self._send("step", (time, inputs, max_advance), {})
        else:
            return await self._send("step", (time, inputs), {})

    async def get_data(self, outputs) -> OutputData:
        return await self._send("get_data", (outputs,), {})

    @abstractmethod
    async def _send(self, func_name: str, args, kwargs) -> Any:
        raise NotImplementedError()

    @abstractmethod
    async def stop(self):
        raise NotImplementedError()


class LocalProxy(APIProxy):
    """
    Proxy for a local simulator. This mainly wraps each mosaik method in a coroutine.
    """
    sim: mosaik_api_v3.Simulator

    def __init__(self, mosaik_remote: MosaikRemote, sim: mosaik_api_v3.Simulator):
        super().__init__(mosaik_remote)
        self.sim = sim
        self._api_compliant = mosaik_api_v3.check_api_compliance(sim)
        sim.mosaik = mosaik_remote  # type: ignore

    async def _send(self, func_name: str, args, kwargs):
        func = getattr(self.sim, func_name)
        # A simulator that makes requests back to mosaik (like set_data or set_event)
        # will have generator functions instead of normal functions as its init, create,
        # step and/or get_data. It will yield coroutines that produce the required
        # information, which we have to await. (This is due to simpy, which used
        # generator functions for its asynchronicity; we didn't want to break the API.)
        # TODO: Maybe check this during __init__ and create the right methods instead of
        # checking for isgeneratorfunction on each call?
        if isgeneratorfunction(func):
            gen = func(*args, **kwargs)
            try:
                evt = next(gen)
                while True:
                    evt = gen.send(await evt)
            except StopIteration as stop:
                return stop.value
        else:
            return func(*args, **kwargs)

    async def stop(self):
        return await self._send("finalize", (), {})


REQUEST = 0
SUCCESS = 1
FAILURE = 2


class RemoteException(Exception):
    pass


class RemoteProxy(APIProxy):
    _reader: asyncio.StreamReader
    _reader_task: asyncio.Task
    _writer: asyncio.StreamWriter
    _pending_requests: Dict[int, asyncio.Future]
    _outgoing_msg_counter: Iterator[int]

    def __init__(
        self,
        mosaik_remote: MosaikRemote,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ):
        super().__init__(mosaik_remote)
        self._reader = reader
        self._writer = writer
        self._pending_requests = {}
        self._outgoing_msg_counter = count()

        self._reader_task = asyncio.get_running_loop().create_task(
            self._receive_forever()
        )

    async def _receive_forever(self):
        try:
            while True:
                msg_type, msg_id, msg = await decode(self._reader)
                if msg_type == REQUEST:
                    func_name, args, kwargs = msg
                    func = getattr(self._mosaik_remote, func_name)
                    try:
                        result = await func(*args, **kwargs)
                        self._writer.write(encode([SUCCESS, msg_id, result]))
                        await self._writer.drain()
                    except Exception as e:
                        self._writer.write(encode([FAILURE, msg_id, str(e)]))
                        await self._writer.drain()
                elif msg_type == SUCCESS:
                    self._pending_requests.pop(msg_id).set_result(msg)
                elif msg_type == FAILURE:
                    self._pending_requests.pop(msg_id).set_exception(
                        RemoteException(msg)
                    )
        except asyncio.IncompleteReadError as e:
            for request in self._pending_requests.values():
                request.set_exception(e)
        except Exception as e:
            logger.error(
                f"Something went wrong in _receive_forever, exception type {type(e)}: "
                f"{e}"
            )
            await self.stop()

    async def _send(self, func_name: str, args, kwargs):
        msg_id = next(self._outgoing_msg_counter)
        self._writer.write(encode([REQUEST, msg_id, [func_name, args, kwargs]]))
        await self._writer.drain()
        result_future = asyncio.get_running_loop().create_future()
        self._pending_requests[msg_id] = result_future
        return await result_future

    async def stop(self):
        msg_id = next(self._outgoing_msg_counter)
        self._writer.write(encode([REQUEST, msg_id, ["stop", [], {}]]))
        await self._writer.drain()
        self._writer.close()
        await self._writer.wait_closed()
        self._reader_task.cancel()
        # TODO: Maybe set some timeout?


encoder = JSONEncoder()


def encode(obj) -> bytes:
    # JSONEncoder encodes to string, then encode that string into bytes
    obj_bytes = encoder.encode(obj).encode()
    return len(obj_bytes).to_bytes(4, 'big') + obj_bytes


decoder = JSONDecoder()


async def decode(reader: asyncio.StreamReader) -> Tuple[int, int, Any]:
    msg_length_bytes = await reader.readexactly(4)
    msg_length = int.from_bytes(msg_length_bytes, 'big')
    msg_bytes = await reader.readexactly(msg_length)
    return tuple(decoder.decode(msg_bytes.decode()))


def validate_api_version(
    version: str
) -> Union[Tuple[int, int], Tuple[int, int, int]]:
    """
    Validate the *version*.

    Raise a :exc: `ScenarioError` if the version format is wrong or
    does not match the min requirements.
    """
    try:
        version_tuple = str(version).split('.')
        v_tuple = tuple(map(int, version_tuple))
    except ValueError:
        raise ScenarioError(f'Version parts of {version} must be integer') from None
    if len(v_tuple) < 2:
        raise ScenarioError(
            'Version must follow at least the format "major.minor" and can optionally '
            f'include the patch version like "major.minor.patch", but is {version}'
        ) from None
    if not (v_tuple[0] == API_MAJOR and v_tuple[1] <= API_MINOR):
        raise ScenarioError(
            f'Version must be between {API_MAJOR}.0 and {API_MAJOR}.{API_MINOR}'
        )

    return v_tuple


def expand_meta(meta: Meta, sim_name: str):
    """
        Checks if (non-)triggering attributes ("(non-)trigger") are given and
        adds them to each model's meta data if necessary.

        Raise a :exc: `ScenarioError` if the given values are not consistent.
        """
    sim_type = meta['type']

    for model, model_meta in meta['models'].items():
        attrs = set(model_meta.get('attrs', []))
        trigger = model_meta.setdefault('trigger', [])
        if trigger is True:
            trigger = attrs
        trigger = set(trigger)
        non_trigger = set(model_meta.get('non-trigger', []))
        overlap = trigger & non_trigger
        if overlap:
            raise ScenarioError(
                "Triggering and non-triggering attributes must not overlap, but "
                f"the following are listed in both for model {model} of simulator "
                f"{sim_name}: {', '.join(overlap)}."
            )
        if trigger and non_trigger:
            if trigger.union(non_trigger) != attrs:
                raise ScenarioError(
                    "Triggering and non-triggering attributes have to be a disjoint "
                    f"split of attrs, but are not for {model} of simulator "
                    f"'{sim_name}'."
                )
        elif trigger:
            if not trigger.issubset(attrs):
                raise ScenarioError(
                    "Triggering attributes must be a subset of attrs, but are not for "
                    f"{model} of simulator {sim_name}."
                )
        elif non_trigger:
            trigger = attrs - non_trigger
        else:
            if sim_type == 'event-based':
                trigger = attrs

        model_meta['trigger'] = trigger

        if sim_type == 'time-based':
            model_meta['persistent'] = attrs
        elif sim_type == 'hybrid':
            non_persistent = model_meta.get('non-persistent', [])
            if non_persistent is True:
                non_persistent = attrs
            non_persistent = set(non_persistent)
            model_meta['persistent'] = attrs - non_persistent
        else:
            model_meta['persistent'] = []

    return meta


def type_check(meta, sim_name, sim_id):
    """
        Checks if  meta's type exists and is correctly set.
        Raise a :exc: `ScenarioError` if the type ist not correct.
        """
    if 'type' not in meta:
        sim_type = meta['type'] = 'time-based'
        meta['old_api'] = True
        logger.warning(
            "DEPRECATION: Simulator {sim_name}'s meta doesn't contain a type. "
            "'{sim_type}' is set as default. This might cause an error in future "
            "releases.",
            sim_name=sim_name,
            sim_type=sim_type
        )
    else:
        types = ['time-based', 'event-based', 'hybrid']
        if meta['type'] not in types:
            typo = meta['type']
            meta['type'] = 'time-based'
            raise ScenarioError(
                f"{sim_id} contains an unknown type: '{typo}'. Please check for typos "
                f"in your Simulators '{sim_name}' meta and scenario."
            )
