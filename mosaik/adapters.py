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

import warnings
from typing import Any, Dict, Optional

from loguru import logger  # noqa: F401  # type: ignore
from mosaik_api_v3.types import Meta, SimId

from mosaik.exceptions import ScenarioError
from mosaik.proxies import BaseProxy, Proxy


async def init_and_get_adapter(
    base_proxy: BaseProxy,
    sid: SimId,
    sim_params: Dict[str, Any],
    explicit_version_str: Optional[str] = None,
) -> Proxy:
    """Initialize the simulator given by ``base_proxy`` (by calling its
    ``init`` function) and wrap it in a ``Proxy`` object that
    adapts it to the current version of mosaik.

    :param base_proxy: The ``BaseProxy`` for this simulator.
    :param sid: The ``SimId`` that was assigned to this simulator.
    :param kwargs: The remaining initialization arguments for the
    simulator.
    :return: The base proxy wrapped in adapters based on the API version
    returned by the simulator's ``init`` function and the meta returned
    by the init call.
    :raise ScenarioError: if there is a problem during initialization.
    """
    if explicit_version_str is not None:
        explicit_version = list(map(int, explicit_version_str.split(".")))
    else:
        explicit_version = None

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
    if explicit_version and version != explicit_version:
        raise ScenarioError(
            f"The explicit version that you specified for simulator {sid} in your "
            f"SimConfig (namely {'.'.join(map(str, explicit_version))}) does not match "
            "the version that this simulator reports (namely "
            f"{'.'.join(map(str, version))})."
        )

    proxy: Proxy = base_proxy
    # Add all the adapters needed to get from the actual version of the
    # simulator to the current version.
    # Note that there are no ``elif``s here since we need to add all
    # required adapters, not just the first matching one.
    # IMPORTANT: Add new adapters at the bottom to ensure the correct
    # nesting!
    if version < [2, 2]:
        proxy = V2ToV1Adapter(proxy)
    if version < [3]:
        proxy = V3ToV2Adapter(proxy)

    # Warn the user if no explicit version was specified in the
    # SIM_CONFIG but the simulator is outdated for this version of
    # mosaik.
    if not isinstance(proxy, BaseProxy) and not explicit_version:
        warnings.warn(
            f"Simulator {sid} is using an outdated API version, namely "
            f"{'.'.join(map(str, version))}. It should still work. You "
            "can suppress this warning by adding an explicit API "
            "version for this simulator in your SimConfig."
        )

    return proxy


class Adapter(Proxy):
    _out: Proxy

    def __init__(self, out: Proxy):
        self._out = out

    @property
    def meta(self) -> Meta:
        return self._out.meta

    async def send(self, request: Any):
        return await self._out.send(request)

    async def stop(self):
        return await self._out.stop()


class V3ToV2Adapter(Adapter):
    """API changes:
    - ``init`` is now supplied with the ``time_resolution`` (as a kwarg)
      (but this is handled in BaseConnection)
    - ``step`` is now supplied with ``max_advance`` (as an arg)
    """

    async def send(self, request: Any):
        try:
            func_name, args, kwargs = request
            if func_name == "step":
                request = ("step", args[0:2], kwargs)
        except ValueError:
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

    async def send(self, request: Any):
        try:
            func_name, _args, _kwargs = request
            if func_name == "setup_done":
                return None
        except ValueError:
            pass

        return await self._out.send(request)
