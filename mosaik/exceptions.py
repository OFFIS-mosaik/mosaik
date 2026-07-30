"""This module provides mosaik-specific exception types.

Exceptions are sorted into two types:

- A :exc:`ScenarioError` indicates that you as the author of the
  scenario have made an error in their setup.
- A :exc:`SimulationError` occurs during the simulation. This often
  indicates that there is an error in a simulator. (But the error
  might also be due to an error in using it.) Check your usage carefully
  (including the simulator's documentation), and then potentially
  contact the simulator author about the error.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from mosaik_api_v3 import SimId
from mosaik_api_v3.types import Attr, FullId

from mosaik.internal_util import doc_link
from mosaik.process_termination_managers import ProcessTerminationManager
from mosaik.tiered_time import TieredTime

if TYPE_CHECKING:
    from mosaik.async_scenario import Entity, StarterConfig


class ScenarioError(Exception):
    """This exception is raised if something fails during the creation
    of a scenario.

    This is usually due to an error on the part of the part of the
    scenario author.
    """


class SimulationError(Exception):
    """This exception is raised if a simulator cannot be started or if
    a problem arises during the execution of a simulation.

    These exceptions can be due to errors in the scenario or due to
    errors in the simulators.
    """

    def __init__(self, msg: str, exc: BaseException | None = None):
        arg = ""
        if exc:
            orig = str(exc)
            if orig.endswith("."):
                orig = orig[:-1]
            arg += f"{orig}: "
        arg += msg
        super().__init__(arg)


class SimulatorError(Exception):
    """This is the supertype for exceptions raised if a simulator does
    not behave correctly.

    If you encounter one of these exceptions as a scenario author, you
    should usually contact the author of the simulator in question to
    resolve the issue.
    """

    simulator: str

    def __init__(self, simulator: str, *args: Any):
        self.simulator = simulator
        super().__init__(*args)


class NonSerializableOutputsError(SimulationError):
    """This exception is raised if a simulator started via ``"python"``
    returns output that cannot be serialized to JSON but you try to
    transmit this data to a simulator started via ``"cmd"`` or
    ``"connect"``.

    There are two possible resolutions:

    - Contact the simulator author to have them change their output
      datatypes to standard Python types that can be serialized.
    - Start the destination simulator via ``"python"`` as well. This
      resolution is mostly sensible if the two simulators are tightly
      coupled and are supposed to exchange non-primitive objects
      directly.
    """

    dest: SimId
    errors: list[tuple[str, str, str, TypeError]]

    def __init__(self, dest: SimId):
        self.dest = dest
        self.errors = []

    def add_error(self, dest_eid: str, dest_attr: str, src_id: str, error: TypeError):
        self.errors.append((dest_eid, dest_attr, src_id, error))

    def __bool__(self):
        return bool(self.errors)

    def __str__(self) -> str:
        return (
            f"Errors while trying to JSON-serialize inputs for {self.dest}:\n"
            + "\n".join(
                f"- serializing output from {src} for {dest_eid}.{dest_attr}: {error!s}"
                for dest_eid, dest_attr, src, error in self.errors
            )
            + "\nThis is likely a problem in the source simulator(s)."
        )


class DuplicateEntityIdError(SimulatorError):
    """This exception is raised if a simulator returns multiple entities
    with the same entity ID."""

    entity_id: str

    def __init__(self, simulator: str, entity_id: str):
        self.entity_id = entity_id
        super().__init__(simulator)

    def __str__(self) -> str:
        return (
            f"Simulator {self.simulator} returned multiple entities "
            f"with entity ID '{self.entity_id}'."
        )


class ConnectionClosedError(SimulatorError):
    """This exception is raised if a simulator closes the socket
    connection (or if it breaks for other reasons) when mosaik is not
    expecting it to be broken.
    """

    method_called: str

    def __init__(self, simulator: str, method_called: str):
        super().__init__(simulator)
        self.method_called = method_called

    def __str__(self) -> str:
        return (
            f"the connection to simulator '{self.simulator}' was broken before or "
            f"during a '{self.method_called}' call"
        )


# --- Errors related to starting and initializing simulators -----------


class SimulatorInitError(ScenarioError):
    """This exception is raised if an error occurs while mosaik is
    calling ``init`` on a simulator. It wraps the original error (which
    might, for example, have been raised by the simulator itself) for
    additional context.
    """

    sim_id: SimId
    cause: BaseException

    def __init__(self, sim_id: SimId, cause: BaseException):
        self.sim_id = sim_id
        self.cause = cause

    def __str__(self) -> str:
        return (
            f"There was an error during the initialization of {self.sim_id}: "
            f"{self.cause}"
        )


class ApiVersionTooNewError(ScenarioError):
    """This exception is raised if a simulator reports an API version
    that is newer than what this version of mosaik supports. Try
    upgrading the mosaik package.
    """

    sim_id: SimId
    version: list[int]

    def __init__(self, sim_id: SimId, version: list[int]):
        self.sim_id = sim_id
        self.version = version

    def __str__(self) -> str:
        version_str = ".".join(map(str, self.version))
        return (
            f"There was an error during the initialization of {self.sim_id}: "
            f"The API version ({version_str}) is too new for this version of "
            "mosaik. Maybe a newer version of the mosaik package is available "
            "to be used in your scenario?"
        )


class ApiVersionMismatchError(ScenarioError):
    """This exception is raised if the API version explicitly specified
    for a simulator (in its :class:`~mosaik.async_scenario.SimConfig`
    entry) does not match the version that the simulator actually
    reports.
    """

    sim_id: SimId
    explicit_version: list[int]
    actual_version: list[int]

    def __init__(
        self,
        sim_id: SimId,
        explicit_version: list[int],
        actual_version: list[int],
    ):
        self.sim_id = sim_id
        self.explicit_version = explicit_version
        self.actual_version = actual_version

    def __str__(self) -> str:
        explicit_str = ".".join(map(str, self.explicit_version))
        actual_str = ".".join(map(str, self.actual_version))
        return (
            f"The explicit version that you specified for simulator {self.sim_id} "
            f"in your SimConfig (namely {explicit_str}) does not match the version "
            f"that this simulator reports (namely {actual_str})."
        )


class ForcedOldApiUsageError(ScenarioError):
    """This exception is raised if a simulator's ``init`` or ``step``
    method is missing the parameters required for API version 3 or
    higher (namely, the ``time_resolution`` keyword parameter of
    ``init`` and the ``max_advance`` parameter of ``step``) but the
    simulator's meta nevertheless claims to support that version.
    """

    sim_id: SimId
    version: list[int]

    def __init__(self, sim_id: SimId, version: list[int]):
        self.sim_id = sim_id
        self.version = version

    def __str__(self) -> str:
        version_str = ".".join(map(str, self.version))
        return (
            "The underlying simulator is not compliant with the high-level API "
            "version 3 (or higher) (because its init method is missing the "
            "time_resolution keyword parameter or its step method is missing the "
            "max_advance parameter), but it claims to be of version "
            f"{version_str} in its meta's api_version field."
        )


# --- Errors related to starting simulators via a Starter --------------


class MissingSimIdError(ScenarioError):
    """This exception is raised if
    :meth:`World.start <mosaik.async_scenario.AsyncWorld.start>` is
    called with a :class:`~mosaik.starters.Starter` object but without
    an explicit ``sim_id``. (A ``sim_id`` cannot be generated
    automatically in this case, as it usually is, because there is no
    simulator name to base it on.)
    """

    def __str__(self) -> str:
        return (
            "when starting a simulator using a Starter, a sim_id must be "
            "specified explicitly"
        )


class MissingSimConfigError(ScenarioError):
    """This exception is raised if a simulator is started by name (i.e.
    by giving a key into the world's ``sim_config``) but no
    ``sim_config`` was specified when the world was created.
    """

    def __str__(self) -> str:
        return (
            "starting simulators by name requires specifying a sim_config when "
            "creating the world"
        )


class UnknownStarterNameError(ScenarioError):
    """This exception is raised if a simulator is started by a name
    that is not defined in the world's ``sim_config``.
    """

    starter_name: str

    def __init__(self, starter_name: str):
        self.starter_name = starter_name

    def __str__(self) -> str:
        return f"no starter '{self.starter_name}' was defined in the sim_config"


class DuplicateSimIdError(ScenarioError):
    """This exception is raised if a simulator is started with a
    ``sim_id`` that has already been used for another simulator in this
    world.
    """

    sim_id: SimId

    def __init__(self, sim_id: SimId):
        self.sim_id = sim_id

    def __str__(self) -> str:
        return f"a simulator with sim_id '{self.sim_id}' has already been started"


# --- Errors related to connecting entities ----------------------------


class WeakConnectionOutsideGroupError(ScenarioError):
    """This exception is raised if a weak connection is created between
    (entities of) two simulators that do not share a simulator group.

    Weak connections are only legal within groups, which clarify whether
    and how weak connections in different parts of the simulation
    interact, see :ref:`weak-connections`.
    """

    def __str__(self) -> str:
        return (
            "Weak connections may only be used in groups. This is new in mosaik "
            "3.3. For more information, see "
            f"{doc_link('scenario-definition', 'weak-connections')}."
        )


class AttributeConnectionError(ScenarioError):
    """This exception is raised if a single attribute connection
    (as established by
    :meth:`~mosaik.async_scenario.AsyncWorld.connect_one`) cannot be
    made, for example because the source or destination attribute does
    not exist, or because a weak or time-shifted connection into a
    non-trigger attribute is missing initial data.
    """

    src: Entity
    dest: Entity
    src_attr: Attr
    dest_attr: Attr
    missing_src_attr: bool
    missing_dest_attr: bool
    missing_initial_data: bool

    def __init__(
        self,
        src: Entity,
        dest: Entity,
        src_attr: Attr,
        dest_attr: Attr,
        missing_src_attr: bool = False,
        missing_dest_attr: bool = False,
        missing_initial_data: bool = False,
    ):
        self.src = src
        self.dest = dest
        self.src_attr = src_attr
        self.dest_attr = dest_attr
        self.missing_src_attr = missing_src_attr
        self.missing_dest_attr = missing_dest_attr
        self.missing_initial_data = missing_initial_data

    @property
    def problems(self) -> list[str]:
        problems: list[str] = []
        if self.missing_src_attr:
            problems.append("the source attribute does not exist")
        if self.missing_dest_attr:
            problems.append("the destination attribute does not exist")
        if self.missing_initial_data:
            problems.append(
                "weak or time-shifted connection into non-trigger attribute "
                "requires initial data"
            )
        return problems

    def __str__(self) -> str:
        return (
            f"There are problems connecting {self.src.full_id}.{self.src_attr} to "
            f"{self.dest.full_id}.{self.dest_attr}:\n- " + "\n- ".join(self.problems)
        )


class ConnectError(ScenarioError):
    """This exception is raised by
    :meth:`~mosaik.async_scenario.AsyncWorld.connect` if one or more of
    the requested attribute connections could not be made. The
    individual errors (usually :class:`AttributeConnectionError`
    instances) are available in :attr:`errors`.
    """

    errors: list[ScenarioError]

    def __init__(self, errors: list[ScenarioError]):
        self.errors = errors

    def __str__(self) -> str:
        return "While connecting entities, the following errors occurred:\n - " + (
            "\n - ".join(str(e) for e in self.errors)
        )


# --- Errors related to the dataflow graph -----------------------------


class DataflowCycleError(ScenarioError):
    """This exception is raised if the connections between simulators
    result in a cyclic dataflow with no delay anywhere in the cycle.
    Such a cycle cannot be resolved during the simulation, as it would
    result in each simulator in the cycle waiting on another one in the
    cycle indefinitely.

    You can resolve such a cycle by making (at least) one of the
    connections in the cycle weak or time-shifted.
    """

    cycle: list[SimId]
    connections: list[tuple[FullId, Attr, FullId, Attr]]

    def __init__(
        self,
        cycle: list[SimId],
        connections: list[tuple[FullId, Attr, FullId, Attr]],
    ):
        self.cycle = cycle
        self.connections = connections

    def __str__(self) -> str:
        connection_report = "\n".join(
            f"- {src_entity}.{src_attr} -> {dest_entity}.{dest_attr}"
            for src_entity, src_attr, dest_entity, dest_attr in self.connections
        )
        return f"Your scenario contains a cycle:\n{connection_report}"


# --- Errors related to a simulator's meta and model factory -----------


class UnknownExtraMethodError(ScenarioError):
    """This exception is raised if you attempt to call an extra method
    on a simulator that is not listed as one of its ``extra_methods``.
    """

    sim_id: SimId
    method_name: str

    def __init__(self, sim_id: SimId, method_name: str):
        self.sim_id = sim_id
        self.method_name = method_name

    def __str__(self) -> str:
        return f"`{self.method_name}` is not an extra method on '{self.sim_id}'"


class MissingSimulatorTypeError(ScenarioError):
    """This exception is raised if a simulator's meta does not specify
    a ``type`` (one of ``"time-based"``, ``"event-based"`` or
    ``"hybrid"``), which is required starting from API version 3.
    """

    sim_id: SimId

    def __init__(self, sim_id: SimId):
        self.sim_id = sim_id

    def __str__(self) -> str:
        return (
            f"The simulator {self.sim_id} is missing a type specification "
            '("time-based", "event-based" or "hybrid"). This is required '
            "starting from API version 3."
        )


class InvalidSimulatorTypeError(ScenarioError):
    """This exception is raised if a simulator's meta specifies a
    ``type`` that is not one of ``"time-based"``, ``"event-based"`` or
    ``"hybrid"``.
    """

    sim_id: SimId
    type: str

    def __init__(self, sim_id: SimId, type: str):
        self.sim_id = sim_id
        self.type = type

    def __str__(self) -> str:
        return (
            f"The type '{self.type}' of simulator {self.sim_id} is not a valid "
            "type. (It should be one of 'time-based', 'event-based' and "
            "'hybrid'.) Please check for typos in your simulator's init function "
            "and meta."
        )


class IllegalModelNameError(ScenarioError):
    """This exception is raised if a simulator declares a model whose
    name clashes with one of the mosaik API methods.
    """

    sim_id: SimId
    model_name: str

    def __init__(self, sim_id: SimId, model_name: str):
        self.sim_id = sim_id
        self.model_name = model_name

    def __str__(self) -> str:
        return (
            f"Simulator {self.sim_id} uses an illegal model name: "
            f"{self.model_name}. This name is already the name of a mosaik API "
            "method."
        )


class IllegalExtraMethodNameError(ScenarioError):
    """This exception is raised if a simulator declares an extra method
    whose name clashes with one of the mosaik API methods or with one
    of the simulator's own models.
    """

    sim_id: SimId
    method_name: str
    clashes_with_model: bool

    def __init__(
        self, sim_id: SimId, method_name: str, clashes_with_model: bool = False
    ):
        self.sim_id = sim_id
        self.method_name = method_name
        self.clashes_with_model = clashes_with_model

    def __str__(self) -> str:
        if self.clashes_with_model:
            reason = "the name of a model of this simulator"
        else:
            reason = "the name of a mosaik API method"
        return (
            f"Simulator {self.sim_id} uses an illegal name for an extra method: "
            f'"{self.method_name}". This is already {reason}.'
        )


# --- Errors related to running a simulation ---------------------------


class SimulatorConnectionLostError(SimulationError):
    """This exception is raised if the connection to a simulator closes
    unexpectedly while mosaik is communicating with it during a
    running simulation.
    """

    sim_id: SimId
    during: str | None

    def __init__(
        self,
        sim_id: SimId,
        cause: BaseException | None = None,
        during: str | None = None,
    ):
        self.sim_id = sim_id
        self.during = during
        if during:
            msg = (
                f"Simulator '{sim_id}' closed its connection while executing {during}."
            )
        else:
            msg = f'Simulator "{sim_id}" closed its connection.'
        super().__init__(msg, cause)


class StepTimeMismatchError(SimulationError):
    """This exception is raised if a simulator is about to perform a
    step at some time but mosaik has previously determined that that
    simulator had already passed that time.

    This usually indicates an internal scheduling error in mosaik;
    please report it on our
    `issue tracker <https://gitlab.com/mosaik/mosaik/issues>`__.
    """

    sim_id: SimId
    step_time: TieredTime
    progress_time: TieredTime

    def __init__(self, sim_id: SimId, step_time: TieredTime, progress_time: TieredTime):
        self.sim_id = sim_id
        self.step_time = step_time
        self.progress_time = progress_time
        super().__init__(
            f"Simulator {sim_id} is trying to perform a step at time "
            f"{step_time}, but it has already progressed to time "
            f"{progress_time}."
        )


class MaxLoopIterationsExceededError(SimulationError):
    """This exception is raised if a simulator performs a sub-step (as
    part of a same-time loop) more often than
    :attr:`~mosaik.async_scenario.AsyncWorld.max_loop_iterations`. This
    usually indicates that the scenario has run into an infinite loop.
    If not,
    :attr:`~mosaik.async_scenario.AsyncWorld.max_loop_iterations` can be
    increased to get rid of this error.
    """

    sim_id: SimId
    max_loop_iterations: int
    step_time: TieredTime

    def __init__(self, sim_id: SimId, max_loop_iterations: int, step_time: TieredTime):
        self.sim_id = sim_id
        self.max_loop_iterations = max_loop_iterations
        self.step_time = step_time
        super().__init__(
            f"Simulator {sim_id} has performed a sub-step more than "
            f"{max_loop_iterations} times. (The complete now is "
            f"{step_time}.) This might indicate that you have run into an "
            "infinite loop. If not, you can increase max_loop_iterations to "
            "get rid of this warning."
        )


class InvalidNextStepTypeError(SimulationError):
    """This exception is raised if the next step time returned by a
    simulator's ``step`` method is not of type ``int``.
    """

    sim_id: SimId
    next_step_time: int

    def __init__(self, sim_id: SimId, next_step_time: int):
        self.sim_id = sim_id
        self.next_step_time = next_step_time
        super().__init__(
            "the next step time returned by the step method must be of type "
            f"int, but is of type {type(next_step_time)} for simulator "
            f'"{sim_id}"'
        )


class InvalidNextStepTimeError(SimulationError):
    """This exception is raised if the next step time returned by a
    simulator's ``step`` method is not later than the time of the step
    that was just performed.
    """

    sim_id: SimId
    next_step_time: int
    current_step_time: int

    def __init__(self, sim_id: SimId, next_step_time: int, current_step_time: int):
        self.sim_id = sim_id
        self.next_step_time = next_step_time
        self.current_step_time = current_step_time
        super().__init__(
            "the next step time returned by step must be later than the "
            f"current step's time, but {next_step_time} <= {current_step_time} "
            f'for simulator "{sim_id}"'
        )


class InvalidOutputTimeError(SimulationError):
    """This exception is raised if a simulator reports an output time
    that is earlier than the time of the step whose output is being
    collected.
    """

    sim_id: SimId
    output_time: int
    last_step_time: TieredTime

    def __init__(self, sim_id: SimId, output_time: int, last_step_time: TieredTime):
        self.sim_id = sim_id
        self.output_time = output_time
        self.last_step_time = last_step_time
        super().__init__(
            f"Output time ({output_time}) is not >= time ({last_step_time}) for "
            f'simulator "{sim_id}".'
        )


# --- Errors related to simulator requests during a running simulation -


class EventInNonRealTimeModeError(SimulationError):
    """This exception is raised if a simulator tries to schedule an
    event (using ``set_event``) in a non-real-time simulation.

    Events can only sensibly be scheduled in real-time mode, as there
    is no relation between the real time at which the event occurs and
    and mosaik's internal simulation time, otherwise.
    """

    sim_id: SimId

    def __init__(self, sim_id: SimId):
        self.sim_id = sim_id
        super().__init__(
            f"Simulator '{sim_id}' tried to set an event in non-real-time mode."
        )


class AsyncRequestsNotConnectedError(ScenarioError):
    """This exception is raised if a simulator tries to make an
    asynchronous request (using ``get_data`` or ``set_data``) to
    another simulator that it is not connected to.
    """

    src_sim_id: SimId
    dest_sim_id: SimId

    def __init__(self, src_sim_id: SimId, dest_sim_id: SimId):
        self.src_sim_id = src_sim_id
        self.dest_sim_id = dest_sim_id

    def __str__(self) -> str:
        return (
            f"No connection from {self.src_sim_id} to {self.dest_sim_id}: You "
            "need to connect entities from both simulators and set "
            "`async_requests=True`."
        )


class AsyncRequestsNotEnabledError(ScenarioError):
    """This exception is raised if a simulator tries to make an
    asynchronous request (using ``get_data`` or ``set_data``) to
    another simulator that it is connected to, but without
    ``async_requests=True`` having been set for that connection.
    """

    src_sim_id: SimId
    dest_sim_id: SimId

    def __init__(self, src_sim_id: SimId, dest_sim_id: SimId):
        self.src_sim_id = src_sim_id
        self.dest_sim_id = dest_sim_id

    def __str__(self) -> str:
        return (
            f"Async. requests not enabled for the connection from "
            f"{self.src_sim_id} to {self.dest_sim_id}. Add the argument "
            f"`async_requests=True` to the connection of entities from "
            f"{self.src_sim_id} to {self.dest_sim_id}."
        )


# --- Errors related to starters ---------------------------------------


class UnknownStarterConfigError(ScenarioError):
    """This exception is raised if a
    :class:`~mosaik.async_scenario.StarterConfig` does not match any of
    the known :class:`~mosaik.starters.Starter` subclasses. (By
    default, it must contain one of the keys ``"python"``, ``"cmd"``,
    or ``"connect"``.)
    """

    starter_config: StarterConfig

    def __init__(self, starter_config: StarterConfig):
        self.starter_config = starter_config

    def __str__(self) -> str:
        return (
            f"Starter config {self.starter_config} does not match any known "
            'starter. (By default, it must contain one of the keys "python", '
            '"cmd", or "connect".)'
        )


class MalformedPythonImportStringError(ScenarioError):
    """This exception is raised if a ``"python"`` starter config's
    import string does not have the form ``"module_name:ClassName"``.
    """

    import_string: str

    def __init__(self, import_string: str):
        self.import_string = import_string

    def __str__(self) -> str:
        return 'malformed import string for python starter, expected "module:Class"'


class PythonImportError(ScenarioError):
    """This exception is raised if the module or class specified for a
    :class:`~mosaik.starters.PythonStarter` could not be imported.
    """

    module_name: str
    class_name: str
    cause: BaseException

    def __init__(self, module_name: str, class_name: str, cause: BaseException):
        self.module_name = module_name
        self.class_name = class_name
        self.cause = cause

    def __str__(self) -> str:
        if isinstance(self.cause, ModuleNotFoundError):
            details = f"could not import module `{self.module_name}`"
        elif isinstance(self.cause, AttributeError):
            details = (
                f"class `{self.class_name}` not found in module `{self.module_name}`"
            )
        else:
            details = f"Error importing the requested class: {self.cause}"
        return f"Simulator could not be started: {details}"


class OutdatedMosaikApiPackageError(ScenarioError):
    """This exception is raised if the installed version of the
    ``mosaik_api_v3`` package is too old to be used with mosaik 3.
    """

    def __str__(self) -> str:
        return "mosaik 3 requires mosaik_api_v3 or newer."


class ConflictingTerminationManagerError(ScenarioError):
    """This exception is raised if both ``auto_terminate`` and
    ``termination_manager`` are specified for a
    :class:`~mosaik.starters.CmdStarter`. As ``auto_terminate`` is just
    a shorthand for choosing one of two built-in termination managers,
    at most one of the two arguments should be given.
    """

    auto_terminate: bool
    termination_manager: ProcessTerminationManager

    def __init__(
        self,
        auto_terminate: bool,
        termination_manager: ProcessTerminationManager,
    ):
        self.auto_terminate = auto_terminate
        self.termination_manager = termination_manager

    def __str__(self) -> str:
        return (
            f"specify at most one of {self.termination_manager} and "
            f"{self.auto_terminate}"
        )


class ProcessStartError(ScenarioError):
    """This exception is raised if the process for a
    :class:`~mosaik.starters.CmdStarter` could not be started, for
    example because the command or the working directory could not be
    found.
    """

    sim_id: SimId
    cause: BaseException

    def __init__(self, sim_id: SimId, cause: BaseException):
        self.sim_id = sim_id
        self.cause = cause

    def __str__(self) -> str:
        # This distinction has to be made due to a change in Python
        # 3.8.0. It might become unnecessary for future releases
        # supporting Python >= 3.8 only.
        if str(self.cause).count(":") == 2:
            detail = self.cause.args[1]  # type: ignore[attr-defined]
        else:
            detail = str(self.cause).split("] ")[1]
        return f'Simulator "{self.sim_id}" could not be started: {detail}'


class MalformedConnectAddressError(ScenarioError):
    """This exception is raised if the address string given for a
    :class:`~mosaik.starters.ConnectStarter` cannot be parsed. It should
    be of the form ``"host:port"``.
    """

    address: str

    def __init__(self, address: str):
        self.address = address

    def __str__(self) -> str:
        return f'Could not parse address "{self.address}" for a ConnectStarter'


class SimulatorStartTimeoutError(SimulationError):
    """This exception is raised if a simulator started via a
    :class:`~mosaik.starters.CmdStarter` does not connect to mosaik
    within the configured ``start_timeout``.
    """

    sim_id: SimId

    def __init__(self, sim_id: SimId):
        self.sim_id = sim_id
        super().__init__(f'Simulator "{sim_id}" did not connect to mosaik in time.')


class SimulatorConnectError(SimulationError):
    """This exception is raised if mosaik could not connect to a
    simulator via a :class:`~mosaik.starters.ConnectStarter`, for
    example because no simulator is listening at the given address.
    """

    sim_id: SimId
    host: str
    port: int

    def __init__(self, sim_id: SimId, host: str, port: int):
        self.sim_id = sim_id
        self.host = host
        self.port = port
        super().__init__(
            f'Simulator "{sim_id}" could not be started: Could not connect to '
            f'"{host}:{port}"'
        )
