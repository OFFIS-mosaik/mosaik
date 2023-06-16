# This module provides a way of introducing new versions of the mosaik
# API without having to check the version of the API everywhere in the
# code. The basic idea is to work on the "request" level, i.e. when it
# has already been turned into a basic Python datatype (usually a tuple
# consisting of the name of the function, the arguments and the keyword
# arguments) but before the request has been encoded into JSON. This
# representation is then adapted by removing fields that are not
# understood by simulators for previous versions. On the way back,
# fields that are not supplied by old simulators can be filled with
# default values that achieve the old behaviour.
#
# A disadvantage of this method is that old simulators will incur an
# extra level of indirection with each new version of the API. However,
# simulators that are up-to-date will not have any additional
# indirection.
#
# When creating a new version of the low-level API, adapt the rest of
# the mosaik code to use it. Then add a V(new)toV(old)Adapter class in
# this file which turns adapts requests conforming to the new version
# into requests conforming to the old version. Also add a version
# check to ``init_and_get_adapter`` that wraps older simulators in
# this new adapter.
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict

from mosaik_api.types import Meta, SimId

from mosaik.exceptions import ScenarioError
from mosaik.proxies import BaseProxy, Proxy


async def init_and_get_adapter(
    base_proxy: BaseProxy,
    sid: SimId,
    sim_params: Dict[str, Any],
) -> Proxy:
    """Initialize the simulator given by ``connection`` (by calling its
    ``init`` function) and wrap it in a ``Connection`` object that
    adapts it to the current version of mosaik.

    :param connection: The ``BaseConnection`` for this simulator.
    :param sid: The ``SimId`` that was assigned to this simulator.
    :param kwargs: The remaining initialization arguments for the
    simulator.
    :return: The connection wrapped in adapters based on the API version
    returned by the simulator's ``init`` function and the meta returned
    by the init call.
    :raise ScenarioError: if there is a problem during initialization.
    """
    try:
        version = await base_proxy.init(sid, **sim_params)
    except ScenarioError as e:
        raise ScenarioError(
            f"There was an error during the initialization of {sid}: ", e
        )

    # version > 3.0
    if version >= [4]:
        raise ScenarioError(
            f"There was an error during the initialization of {sid}: "
            f"The API version ({'.'.join(map(str, version))}) is too new for this "
            "version of mosaik. Maybe a newer version of the mosaik package is "
            "available to be used in your scenario?"
        )

    proxy: Proxy = base_proxy
    # Add all the adapters needed to get from the actual version of the
    # simulator to the current version.
    # Note that there are no ``elif``s here since we need to add all
    # required adapters, not just the first matching one.
    # IMPORTANT: Add new tests at the end to ensure the correct nesting!
    if version < [2, 2]:
        proxy = V2ToV1Adapter(proxy)
    if version < [3]:
        proxy = V3ToV2Adapter(proxy)

    return proxy


class Adapter(Proxy):
    _out: Proxy
    
    def __init__(self, out: Proxy):
        self._out = out

    @property
    def meta(self) -> Meta:
        return self._out.meta

    async def send(self, request):
        return await self._out.send(request)

    async def stop(self):
        return await self._out.stop()


class V3ToV2Adapter(Adapter):
    """API changes:
    - ``init`` is now supplied with the ``time_resolution`` (as a kwarg)
      (but this is handled in BaseConnection)
    - ``step`` is now supplied with ``max_advance`` (as an arg)
    """
    async def send(self, request):
        try:
            func_name, args, kwargs = request
            if func_name == "step":
                request = ("step", args[0:2], kwargs)
        except:
            pass
        return await self._out.send(request)

    @property
    def meta(self) -> Meta:
        self._out.meta.setdefault("type", "time-based")
        return self._out.meta


class V2ToV1Adapter(Adapter):
    """API changes:
    - ``setup_done`` function was added to simulators
    """
    async def send(self, request):
        try:
            func_name, args, kwargs = request
            if func_name == "setup_done":
                return None
        except:
            pass

        return await self._out.send(request)
