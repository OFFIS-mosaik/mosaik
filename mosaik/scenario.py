"""
This module provides the interface for users to create simulation
scenarios for mosaik.

The :class:`World` holds all necessary data for the simulation and
allows the user to start simulators. It provides a :class:`ModelFactory`
(and a :class:`ModelMock`) via which the user can instantiate model
instances (*entities*). The method :meth:`World.run()` finally starts
the simulation.
"""

from __future__ import annotations

import asyncio
import functools
from types import TracebackType
from typing import (
    Any,
    Awaitable,
    Callable,
    Dict,
    Iterable,
    Optional,
    Tuple,
    Type,
    Union,
)

from mosaik_api_v3.types import Attr, ModelName, SimId
from typing_extensions import Literal

from mosaik.async_scenario import (
    SENTINEL,
    AsyncModelFactory,
    AsyncModelMock,
    AsyncWorld,
    Entity,
    MosaikConfig,
    SimConfig,
)
from mosaik.in_or_out_set import InOrOutSet


class World:
    """
    The world holds all data required to specify and run the scenario.

    We recommend that you use the world in a ``with`` block like so::

        with mosaik.World(SIM_CONFIG) as world:
            # Scenario setup ...

            world.run(until=UNTIL)

    This way, mosaik will keep the connection to the simulators alive
    until the end of the with block and you can still call extra methods
    on the to retrieve final simulation data, if needed.

    However, you can also use a ``World`` outside of a ``with`` block.

    The ``World`` provides a method to start a simulator process
    (:meth:`~World.start`) and manages the simulator instances.

    You have to provide a *sim_config* which tells the world which
    simulators are available and how to start them. See
    :func:`mosaik.simmanager.start` for more details.

    *mosaik_config* can be a dict or list of key-value pairs to set
    addional parameters overriding the defaults::

        {
            'addr': ('127.0.0.1', 5555),
            'start_timeout': 2,  # seconds
            'stop_timeout': 2,   # seconds
        }

    Here, *addr* is the network address that mosaik will bind its socket
    to. *start_timeout* and *stop_timeout* specifiy a timeout (in
    seconds) for starting/stopping external simulator processes.

    If *execution_graph* is set to ``True``, an execution graph will be
    created during the simulation. This may be useful for debugging and
    testing. Note, that this increases the memory consumption and
    simulation time.

    Using the *skip_greetings* and *configure_logging* parameters, you
    can configure how "wordy" mosaik will be. If you set
    *skip_greetings* to ``True``, the big mosaik logo will no longer be
    shown when you create the world. If you set *configure_logging* to
    ``False``, mosaik's logging messages will not be enabled in loguru.
    You can still do this yourself by calling
    ``logger.enable("mosaik")``.
    """

    loop: asyncio.AbstractEventLoop
    _async_world: AsyncWorld
    _no_shutdown_in_run: bool = False

    def __init__(
        self,
        sim_config: SimConfig,
        mosaik_config: Optional[MosaikConfig] = None,
        time_resolution: float = 1.0,
        debug: bool = False,
        cache: bool = True,
        max_loop_iterations: int = 100,
        skip_greetings: bool = False,
        configure_logging: bool = True,
        asyncio_loop: Optional[asyncio.AbstractEventLoop] = None,
    ):
        if asyncio_loop:
            self.loop = asyncio_loop
        else:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)

        self._async_world = AsyncWorld(
            sim_config,
            mosaik_config=mosaik_config,
            time_resolution=time_resolution,
            debug=debug,
            cache=cache,
            max_loop_iterations=max_loop_iterations,
            configure_logging=configure_logging,
            skip_greetings=skip_greetings,
        )

    def __enter__(self):
        self._no_shutdown_in_run = True
        return self

    def __exit__(self, exc_type: Type[Exception], exc: Exception, tb: TracebackType):
        self.shutdown()
        # Don't suppress exceptions. Later on, we might want to add
        # handling of mosaik exceptions here. (Make sure to unify
        # this with the handling in `AsyncWorld`'s `__aexit__`.)
        return False

    def group(self, group_name: str | None = None):
        return self._async_world.group(group_name=group_name)

    def start(
        self,
        sim_name: str,
        sim_id: Optional[SimId] = None,
        **sim_params: Any,
    ) -> ModelFactory:
        """
        Start the simulator named *sim_name* and return a
        :class:`ModelFactory` for it.
        """
        async_model_factory = self.loop.run_until_complete(
            self._async_world.start(sim_name, sim_id, **sim_params)
        )
        return ModelFactory(async_model_factory, self.loop)

    def connect_one(
        self,
        src: Entity,
        dest: Entity,
        src_attr: Attr,
        dest_attr: Optional[Attr] = None,
        time_shifted: Union[bool, int] = False,
        weak: bool = False,
        initial_data: Any = SENTINEL,
        transform: Callable[[Any], Any] = lambda x: x,
    ):
        return self._async_world.connect_one(
            src, dest, src_attr, dest_attr, time_shifted, weak, initial_data, transform
        )

    def connect_async_requests(self, src: ModelFactory, dest: ModelFactory):
        return self._async_world.connect_async_requests(
            src._async_model_factory, dest._async_model_factory
        )

    def connect(
        self,
        src: Entity,
        dest: Entity,
        *attr_pairs: Union[str, Tuple[str, str]],  # type: ignore
        async_requests: bool = False,
        time_shifted: Union[bool, int] = False,
        initial_data: Dict[Attr, Any] = {},
        weak: bool = False,
        transform: Callable[[Any], Any] = lambda x: x,
    ):
        """
        .. warning::
            The keyword *async_requests* is deprecated and will be
            removed in a future release. Implement cyclic data flow
            using time-shifted and weak connections instead.

        Connect the *src* entity to *dest* entity.

        Establish a data-flow for each ``(src_attr, dest_attr)`` tuple
        in *attr_pairs*. If *src_attr* and *dest_attr* have the same
        name, you can optionally only pass one of them as a single
        string.

        Raise a :exc:`~mosaik.exceptions.ScenarioError` if both entities
        share the same simulator instance, if at least one (src. or
        dest.) attribute in *attr_pairs* does not exist, or if the
        connection would introduce a cycle in the data-flow (e.g.,
        A → B → C → A).

        If the *dest* simulator may make asynchronous requests to mosaik
        to query data from *src* (or set data to it), *async_requests*
        should be set to ``True`` so that the *src* simulator stays in
        sync with *dest*.

        An alternative to asynchronous requests are time-shifted
        connections. Their data flow is always resolved after normal
        connections so that cycles in the data-flow can be realized
        without introducing deadlocks. For such a connection
        *time_shifted* should be set to ``True`` and *initial_data*
        should contain a dict with input data for the first simulation
        step of the receiving simulator.

        An alternative to using async_requests to realize cyclic
        data-flow is given by the time_shifted kwarg. If set to ``True``
        it marks the connection as cycle-closing (e.g. C → A). It must
        always be used with initial_data specifying a dict with the data
        sent to the destination simulator at the first step (e.g.
        *{'src_attr': value}*).
        """
        return self._async_world.connect(
            src,
            dest,
            *attr_pairs,
            async_requests=async_requests,
            time_shifted=time_shifted,
            initial_data=initial_data,
            weak=weak,
            transform=transform,
        )

    def set_initial_event(self, sid: SimId, time: int = 0):
        """
        Set an initial step for simulator *sid* at time *time*
        (default=0).
        """
        return self._async_world.set_initial_event(sid, time)

    def get_data(
        self,
        entity_set: Iterable[Entity],
        *attributes: Attr,
    ) -> Dict[Entity, Dict[Attr, Any]]:
        """
        Get and return the values of all *attributes* for each entity of
        an *entity_set*.

        The return value is a dict mapping the entities of *entity_set*
        to dicts containing the values of each attribute in
        *attributes*::

            {
                Entity(...): {
                    'attr_1': 'val_1',
                    'attr_2': 'val_2',
                    ...
                },
                ...
            }
        """
        return self.loop.run_until_complete(
            self._async_world.get_data(entity_set, *attributes)
        )

    def run(
        self,
        until: int,
        rt_factor: Optional[float] = None,
        rt_strict: bool = False,
        print_progress: Union[bool, Literal["individual"]] = True,
        lazy_stepping: bool = True,
        *,
        shutdown: bool = True,
    ):
        """
        Start the simulation until the simulation time ``until`` is
        reached. As mosaik has no way of resetting the simulators to
        their starting state, this method can only be called once.

        :param until: The end time for the simulation, exclusive (i.e.
            the step at time ``until`` will *not* be performed.)
        :param rt_factor: In order to perform real-time simulations,
            you can set ``rt_factor`` to a number > 0. A real-time
            factor of 1. means that 1 second in simulated time takes 1
            second in real-time. An real-time factor of 0.5 will let the
            simulation run twice as fast as real-time. For correct
            behavior of the ``rt_factor``, the time resolution of the
            scenario has to be set adequately, which is 1. [second] by
            default.
        :param rt_strict: If the simulators are too slow for the
            real-time factor you chose, mosaik will emit a warning.
            If you want it to raise a :exc:`RuntimeError`, instead, you
            can set ``rt_strict`` to ``True``.
        :param print_progress: This controls whether progress bars are
            printed while the simulation is running. The default is to
            print one bar representing the global progress of the
            simulation. You can also set ``print_progress='individual'``
            to get one bar per simulator in your simulation (in addition
            to the global one). ``print_progress=False`` turns off the
            progress bars completely. The progress bars use
            `tqdm <https://pypi.org/project/tqdm/>`_; see their
            documentation on how to write to the console without
            interfering with the bars.
        :param lazy_stepping: If ``True`` a simulator can only run ahead
            one step of it's successors. If ``False`` a simulator always
            steps as soon as all input is provided. This might decrease
            the simulation time but increase the memory consumption.
        :param shutdown: If ``True`` and this :class:`World` is not
            being used in a ``with`` block, mosaik will stop all
            simulators and close the connections to them at the end of
            the simulation run. You can set this to ``False`` if you
            want to keep the connections open and call :meth:`shutdown`
            yourself, later. (This is useful if you want to call extra
            methods on your simulator after the simulation is over;
            however, we recommend that you use the :class:`World` in a
            ``with`` block.)

        :raise RuntimeError: if this world has already been run
        """
        if self.loop.is_closed():
            raise RuntimeError(
                "Simulation has already been run and can only be run once for a World "
                "instance."
            )
        self.loop.run_until_complete(
            self._async_world.run(
                until, rt_factor, rt_strict, print_progress, lazy_stepping
            )
        )
        if shutdown and not self._no_shutdown_in_run:
            self.shutdown()

    def shutdown(self):
        """
        Shut-down all simulators and close the server socket.
        """
        if not self.loop.is_closed():
            self.loop.run_until_complete(self._async_world.shutdown())
            self.loop.close()

    @property
    def execution_graph(self):
        return self._async_world.execution_graph

    @property
    def entity_graph(self):
        """The graph of all entities. See :attr:`AsyncWorld.entity_graph
        <mosaik.async_scenario.AsyncWorld.entity_graph>."""
        return self._async_world.entity_graph

    @property
    def sims(self):
        return self._async_world.sims

    @property
    def time_resolution(self):
        return self._async_world.time_resolution

    @property
    def sim_config(self):
        return self._async_world.sim_config

    @property
    def config(self):
        return self._async_world.config


class ModelFactory:
    """
    This is a facade for a simulator *sim* that allows the user to
    create new model instances (entities) within that simulator.

    For every model that a simulator publicly exposes, the
    :class:`ModelFactory` provides a :class:`ModelMock` attribute that
    actually creates the entities.

    If you access an attribute that is not a model or if the model is
    not marked as *public*, an :exc:`~mosaik.exceptions.ScenarioError`
    is raised.
    """

    _async_model_factory: AsyncModelFactory
    _loop: asyncio.AbstractEventLoop

    def __init__(
        self, async_model_factory: AsyncModelFactory, loop: asyncio.AbstractEventLoop
    ):
        self._async_model_factory = async_model_factory
        self._loop = loop

        for name in self._async_model_factory.call:

            def get_wrapper(
                method: Callable[..., Awaitable[Any]],
            ) -> Callable[..., Any]:
                @functools.wraps(method)
                def wrapper(*args: Any, **kwargs: Any):
                    return self._loop.run_until_complete(method(*args, **kwargs))

                return wrapper

            setattr(
                self, name, get_wrapper(getattr(self._async_model_factory.call, name))
            )

    @property
    def _sid(self) -> SimId:
        return self._async_model_factory._sid

    @property
    def type(self) -> Literal["time-based", "event-based", "hybrid"]:
        return self._async_model_factory.type

    def __getattr__(self, name: str) -> ModelMock:
        value = getattr(self._async_model_factory, name)

        if isinstance(value, AsyncModelMock):
            return ModelMock(value, self._loop)

        return value


class ModelMock(object):
    """
    Instances of this class are exposed as attributes of
    :class:`ModelFactory` and allow the instantiation of simulator
    models.

    You can *call* an instance of this class to create exactly one
    entity: ``sim.ModelName(x=23)``. Alternatively, you can use the
    :meth:`create` method to create multiple entities with the same set
    of parameters at once: ``sim.ModelName.create(3, x=23)``.
    """

    _async_model_mock: AsyncModelMock
    _loop: asyncio.AbstractEventLoop

    def __init__(
        self, async_model_mock: AsyncModelMock, loop: asyncio.AbstractEventLoop
    ):
        self._async_model_mock = async_model_mock
        self._loop = loop

    @property
    def event_inputs(self) -> InOrOutSet[Attr]:
        return self._async_model_mock.event_inputs

    @property
    def measurement_inputs(self) -> InOrOutSet[Attr]:
        return self._async_model_mock.measurement_inputs

    @property
    def event_outputs(self) -> InOrOutSet[Attr]:
        return self._async_model_mock.event_outputs

    @property
    def measurement_outputs(self) -> InOrOutSet[Attr]:
        return self._async_model_mock.measurement_outputs

    @property
    def input_attrs(self) -> InOrOutSet[Attr]:
        return self._async_model_mock.input_attrs

    @property
    def output_attrs(self) -> InOrOutSet[Attr]:
        return self._async_model_mock.output_attrs

    @property
    def name(self) -> ModelName:
        return self._async_model_mock.name

    def __call__(self, **model_params: Any):
        """
        Call :meth:`create()` to instantiate one model.
        """
        return self._loop.run_until_complete(self._async_model_mock(**model_params))

    def create(self, num: int, **model_params: Any):
        """
        Create *num* entities with the specified *model_params* and
        return a list with the entity dicts.

        The returned list of entities is the same as returned by
        :meth:`mosaik_api_v3.Simulator.create`, but the simulator is
        prepended to every entity ID to make them globally unique.
        """
        return self._loop.run_until_complete(
            self._async_model_mock.create(num, **model_params)
        )
