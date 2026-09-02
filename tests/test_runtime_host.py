"""Tests for the synchronous foreground Runtime Host lifecycle."""

import ast
from pathlib import Path

import pytest

from atreus.bootstrap.bootstrap import Bootstrap
from atreus.events.event_bus import InProcessEventBus
from atreus.events.models import Event, PublicationResult
from atreus.interfaces.foreground_interface import ForegroundInterface
from atreus.runtime.exceptions import (
    InvalidRuntimeLifecycleTransitionError,
    RuntimeShutdownError,
    RuntimeStartupError,
)
from atreus.runtime.host import RuntimeHost
from atreus.runtime.models import (
    RuntimeFailed,
    RuntimeLifecycleState,
    RuntimeStarted,
    RuntimeStarting,
    RuntimeStopped,
    RuntimeStopping,
)
from tests.support import (
    FixedClock,
    RecordingApplicationLauncher,
    RecordingApplicationStateReader,
    RecordingLogWriter,
)

type LifecycleEvent = (
    RuntimeStarting
    | RuntimeStarted
    | RuntimeStopping
    | RuntimeStopped
    | RuntimeFailed
)

_LIFECYCLE_EVENT_TYPES = (
    RuntimeStarting,
    RuntimeStarted,
    RuntimeStopping,
    RuntimeStopped,
    RuntimeFailed,
)


class StubForegroundInterface(ForegroundInterface):
    """Return or raise one configured foreground result."""

    def __init__(
        self,
        exit_status: int = 0,
        error: BaseException | None = None,
    ) -> None:
        """Initialize deterministic foreground behavior."""
        self._exit_status = exit_status
        self._error = error
        self.run_count = 0

    def run(self) -> int:
        """Record execution and return or raise configured behavior."""
        self.run_count += 1
        if self._error is not None:
            raise self._error
        return self._exit_status


class SelectivelyFailingEventBus(InProcessEventBus):
    """Fail publication for one configured lifecycle event type."""

    def __init__(self, failed_event_type: type[Event]) -> None:
        """Initialize the selective publication failure."""
        super().__init__()
        self._failed_event_type = failed_event_type

    def publish(self, event: Event) -> PublicationResult:
        """Raise for the selected event and delegate all other events."""
        if isinstance(event, self._failed_event_type):
            raise OSError("private event publication detail")
        return super().publish(event)


def record_lifecycle_events(
    event_bus: InProcessEventBus,
) -> list[LifecycleEvent]:
    """Subscribe one collection to every Runtime Host event."""
    events: list[LifecycleEvent] = []
    for event_type in _LIFECYCLE_EVENT_TYPES:
        event_bus.subscribe(event_type, events.append)
    return events


def test_runtime_host_initial_state_is_created() -> None:
    host = RuntimeHost(StubForegroundInterface(), InProcessEventBus())

    assert host.state is RuntimeLifecycleState.CREATED


def test_runtime_host_start_transitions_to_running() -> None:
    event_bus = InProcessEventBus()
    events = record_lifecycle_events(event_bus)
    host = RuntimeHost(StubForegroundInterface(), event_bus)

    host.start()

    assert host.state is RuntimeLifecycleState.RUNNING
    assert [type(event) for event in events] == [RuntimeStarting, RuntimeStarted]
    assert [event.lifecycle_state for event in events] == [
        RuntimeLifecycleState.STARTING,
        RuntimeLifecycleState.RUNNING,
    ]


def test_runtime_host_stop_transitions_running_host_to_stopped() -> None:
    event_bus = InProcessEventBus()
    events = record_lifecycle_events(event_bus)
    host = RuntimeHost(StubForegroundInterface(), event_bus)
    host.start()

    host.stop()

    assert host.state is RuntimeLifecycleState.STOPPED
    assert [type(event) for event in events] == [
        RuntimeStarting,
        RuntimeStarted,
        RuntimeStopping,
        RuntimeStopped,
    ]


def test_runtime_host_rejects_double_start() -> None:
    host = RuntimeHost(StubForegroundInterface(), InProcessEventBus())
    host.start()

    with pytest.raises(InvalidRuntimeLifecycleTransitionError):
        host.start()


def test_runtime_host_can_stop_before_start() -> None:
    event_bus = InProcessEventBus()
    events = record_lifecycle_events(event_bus)
    host = RuntimeHost(StubForegroundInterface(), event_bus)

    host.stop()

    assert host.state is RuntimeLifecycleState.STOPPED
    assert [type(event) for event in events] == [RuntimeStopping, RuntimeStopped]


def test_runtime_host_repeated_stop_is_idempotent() -> None:
    event_bus = InProcessEventBus()
    events = record_lifecycle_events(event_bus)
    host = RuntimeHost(StubForegroundInterface(), event_bus)
    host.stop()

    host.stop()

    assert host.state is RuntimeLifecycleState.STOPPED
    assert [type(event) for event in events] == [RuntimeStopping, RuntimeStopped]


def test_runtime_host_startup_failure_is_sanitized_and_terminal() -> None:
    event_bus = SelectivelyFailingEventBus(RuntimeStarting)
    events = record_lifecycle_events(event_bus)
    host = RuntimeHost(StubForegroundInterface(), event_bus)

    with pytest.raises(RuntimeStartupError, match="Runtime Host startup failed"):
        host.start()

    assert host.state is RuntimeLifecycleState.FAILED
    assert len(events) == 1
    assert isinstance(events[0], RuntimeFailed)
    assert events[0].failure_stage == "startup"
    assert events[0].error_type == "OSError"


def test_runtime_host_shutdown_failure_is_sanitized_and_terminal() -> None:
    event_bus = SelectivelyFailingEventBus(RuntimeStopping)
    events = record_lifecycle_events(event_bus)
    host = RuntimeHost(StubForegroundInterface(), event_bus)
    host.start()

    with pytest.raises(RuntimeShutdownError, match="Runtime Host shutdown failed"):
        host.stop()

    assert host.state is RuntimeLifecycleState.FAILED
    assert [type(event) for event in events] == [
        RuntimeStarting,
        RuntimeStarted,
        RuntimeFailed,
    ]


def test_runtime_host_normal_run_stops_cleanly() -> None:
    foreground = StubForegroundInterface()
    host = RuntimeHost(foreground, InProcessEventBus())

    assert host.run() == 0
    assert host.state is RuntimeLifecycleState.STOPPED
    assert foreground.run_count == 1


@pytest.mark.parametrize("error", (EOFError(), KeyboardInterrupt()))
def test_runtime_host_input_termination_stops_cleanly(error: BaseException) -> None:
    host = RuntimeHost(
        StubForegroundInterface(error=error),
        InProcessEventBus(),
    )

    assert host.run() == 0
    assert host.state is RuntimeLifecycleState.STOPPED


def test_runtime_host_unexpected_foreground_failure_returns_nonzero() -> None:
    event_bus = InProcessEventBus()
    events = record_lifecycle_events(event_bus)
    host = RuntimeHost(
        StubForegroundInterface(error=RuntimeError("private input detail")),
        event_bus,
    )

    assert host.run() == 1
    assert host.state is RuntimeLifecycleState.FAILED
    assert isinstance(events[-1], RuntimeFailed)
    assert events[-1].failure_stage == "foreground_interface"
    assert events[-1].error_type == "RuntimeError"
    assert "private input detail" not in repr(events[-1])


def test_runtime_host_nonzero_foreground_status_is_fatal() -> None:
    host = RuntimeHost(StubForegroundInterface(exit_status=2), InProcessEventBus())

    assert host.run() == 1
    assert host.state is RuntimeLifecycleState.FAILED


def test_composed_host_executes_pipeline_only_while_running() -> None:
    inputs = iter(("open calculator", "exit"))
    controller = RecordingApplicationLauncher()
    writer = RecordingLogWriter()
    host = Bootstrap(
        application_launcher=controller,
        application_state_reader=RecordingApplicationStateReader(),
        clock=FixedClock(),
        log_writer=writer,
    ).compose_host(lambda prompt: next(inputs), lambda output: None)

    assert host.run() == 0

    assert host.state is RuntimeLifecycleState.STOPPED
    assert len(controller.calls) == 1
    assert [record.event_type for record in writer.records[:2]] == [
        "RuntimeStarting",
        "RuntimeStarted",
    ]
    assert [record.event_type for record in writer.records[-2:]] == [
        "RuntimeStopping",
        "RuntimeStopped",
    ]


def test_runtime_host_failure_observability_is_sanitized() -> None:
    writer = RecordingLogWriter()

    def fail_input(prompt: str) -> str:
        raise RuntimeError("private terminal and environment detail")

    host = Bootstrap(
        application_launcher=RecordingApplicationLauncher(),
        application_state_reader=RecordingApplicationStateReader(),
        clock=FixedClock(),
        log_writer=writer,
    ).compose_host(fail_input, lambda output: None)

    assert host.run() == 1

    failed_record = writer.records[-1]
    assert failed_record.event_type == "RuntimeFailed"
    assert failed_record.lifecycle_state == "FAILED"
    assert failed_record.reason_code == "foreground_interface:RuntimeError"
    assert "private terminal" not in repr(failed_record)


def test_always_on_v0_adds_no_concurrent_runtime_mechanism() -> None:
    source_files = (
        Path("src/atreus/runtime/host.py"),
        Path("src/atreus/runtime/console.py"),
        Path("src/atreus/bootstrap/bootstrap.py"),
    )

    for source_file in source_files:
        tree = ast.parse(source_file.read_text(encoding="utf-8"))
        imported_roots = {
            alias.name.partition(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in node.names
        }
        assert "threading" not in imported_roots
        assert "asyncio" not in imported_roots


def test_core_does_not_depend_on_runtime_host() -> None:
    core_source = Path("src/atreus/core/core.py").read_text(encoding="utf-8")

    assert "RuntimeHost" not in core_source
    assert "runtime.host" not in core_source
