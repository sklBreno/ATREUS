"""Tests for controlled application status observation."""

import subprocess
from dataclasses import FrozenInstanceError
from uuid import uuid4

import pytest

from atreus.ai.models import (
    AIProviderAvailability,
    AIProviderAvailabilityState,
)
from atreus.capability.application_status import ApplicationStatusCapability
from atreus.capability.contracts import (
    APPLICATION_ID_ARGUMENT,
    APPLICATION_STATUS_CAPABILITY_ID,
    CapabilityArgument,
)
from atreus.capability.registry import InMemoryCapabilityRegistry
from atreus.context.models import (
    ContextSignalStatus,
    ContextSnapshot,
    ContextType,
)
from atreus.execution.exceptions import MissingCapabilityPermissionsError
from atreus.execution.models import CapabilityExecutionStatus, CapabilityInvocation
from atreus.execution.runtime import InProcessCapabilityRuntime
from atreus.interfaces.application_state_reader import ApplicationStateReader
from atreus.shared.cancellation import StaticCancellationSignal
from atreus.system.exceptions import (
    InvalidSystemOperationError,
    SystemNativeAdapterError,
    SystemOperationCancelledError,
    SystemPermissionDeniedError,
    UnsupportedSystemOperationError,
)
from atreus.system.models import (
    APPLICATION_READ_PERMISSION,
    ApplicationIdentifier,
    ApplicationState,
    ApplicationStatusRequest,
    ApplicationStatusResult,
    SystemOperationContext,
)
from atreus.system.windows_application_state_reader import (
    WindowsApplicationStateReader,
)
from tests.support import (
    NOW,
    FixedClock,
    RecordingApplicationStateReader,
    StaticAIAvailabilityProvider,
)


def make_runtime(
    reader: ApplicationStateReader,
) -> tuple[InProcessCapabilityRuntime, InMemoryCapabilityRegistry]:
    """Create a Runtime loaded with the read-only status capability."""
    registry = InMemoryCapabilityRegistry()
    runtime = InProcessCapabilityRuntime(
        registry,
        StaticAIAvailabilityProvider(
            AIProviderAvailability(AIProviderAvailabilityState.UNAVAILABLE)
        ),
        StaticCancellationSignal(),
        FixedClock(),
    )
    runtime.load((ApplicationStatusCapability(reader),))
    return runtime, registry


def make_invocation(
    application_id: str = "calculator",
    grants: tuple[str, ...] = (APPLICATION_READ_PERMISSION,),
) -> CapabilityInvocation:
    """Create one application-status invocation."""
    return CapabilityInvocation(
        invocation_id=uuid4(),
        request_id=uuid4(),
        plan_id=uuid4(),
        step_id="step-1",
        capability_id=APPLICATION_STATUS_CAPABILITY_ID,
        arguments=(CapabilityArgument(APPLICATION_ID_ARGUMENT, application_id),),
        context=ContextSnapshot(
            ContextType.WORKING,
            0.9,
            NOW,
            NOW,
            ContextSignalStatus.AVAILABLE,
        ),
        timeout_seconds=None,
        permission_grants=grants,
    )


def make_context(
    *,
    grants: tuple[str, ...] = (APPLICATION_READ_PERMISSION,),
    cancelled: bool = False,
) -> SystemOperationContext:
    """Create one controlled status operation context."""
    return SystemOperationContext(
        uuid4(),
        uuid4(),
        APPLICATION_STATUS_CAPABILITY_ID,
        grants,
        StaticCancellationSignal(cancelled),
    )


def test_runtime_loading_registers_application_status_capability() -> None:
    _, registry = make_runtime(RecordingApplicationStateReader())

    metadata = registry.get(APPLICATION_STATUS_CAPABILITY_ID)

    assert metadata is not None
    assert metadata.permissions == (APPLICATION_READ_PERMISSION,)
    assert metadata.requires_ai is False


def test_application_status_contracts_are_immutable_and_typed() -> None:
    request = ApplicationStatusRequest(ApplicationIdentifier.NOTEPAD)
    result = ApplicationStatusResult(
        ApplicationIdentifier.NOTEPAD,
        ApplicationState.RUNNING,
    )

    with pytest.raises(FrozenInstanceError):
        result.state = ApplicationState.NOT_RUNNING  # type: ignore[misc]

    assert hasattr(request, "__slots__")
    assert hasattr(result, "__slots__")
    assert result.application_id is request.application_id


@pytest.mark.parametrize("state", tuple(ApplicationState))
def test_runtime_invokes_status_through_read_only_system_boundary(
    state: ApplicationState,
) -> None:
    reader = RecordingApplicationStateReader(state)
    runtime, _ = make_runtime(reader)

    result = runtime.invoke(make_invocation("notepad"))

    assert result.status is CapabilityExecutionStatus.SUCCEEDED
    assert result.output is not None
    assert tuple((item.name, item.value) for item in result.output) == (
        ("application_id", "notepad"),
        ("state", state.value),
    )
    request, context = reader.calls[0]
    assert request.application_id is ApplicationIdentifier.NOTEPAD
    assert context.capability_id == APPLICATION_STATUS_CAPABILITY_ID
    assert context.permission_grants == (APPLICATION_READ_PERMISSION,)


def test_runtime_enforces_application_read_permission() -> None:
    reader = RecordingApplicationStateReader()
    runtime, _ = make_runtime(reader)

    with pytest.raises(MissingCapabilityPermissionsError):
        runtime.invoke(make_invocation(grants=()))

    assert reader.calls == []


def test_runtime_rejects_spotify_status_before_system_boundary() -> None:
    reader = RecordingApplicationStateReader(ApplicationState.RUNNING)
    runtime, _ = make_runtime(reader)

    result = runtime.invoke(make_invocation("spotify"))

    assert result.status is CapabilityExecutionStatus.FAILED
    assert result.error_code == "capability_execution_failed"
    assert reader.calls == []


class InconsistentApplicationStateReader(ApplicationStateReader):
    """Return a valid typed result for the wrong approved application."""

    def read_status(
        self,
        request: ApplicationStatusRequest,
        context: SystemOperationContext,
    ) -> ApplicationStatusResult:
        """Return a deliberately inconsistent result."""
        return ApplicationStatusResult(
            ApplicationIdentifier.CALCULATOR,
            ApplicationState.RUNNING,
        )


def test_capability_rejects_inconsistent_system_result() -> None:
    runtime, _ = make_runtime(InconsistentApplicationStateReader())

    result = runtime.invoke(make_invocation("notepad"))

    assert result.status is CapabilityExecutionStatus.FAILED
    assert result.error_code == "capability_execution_failed"


@pytest.mark.parametrize(
    ("application_id", "process_names", "expected_state"),
    (
        (
            ApplicationIdentifier.CALCULATOR,
            ("CalculatorApp.exe",),
            ApplicationState.RUNNING,
        ),
        (
            ApplicationIdentifier.CALCULATOR,
            ("explorer.exe",),
            ApplicationState.NOT_RUNNING,
        ),
        (
            ApplicationIdentifier.NOTEPAD,
            ("NOTEPAD.EXE",),
            ApplicationState.RUNNING,
        ),
        (
            ApplicationIdentifier.NOTEPAD,
            ("explorer.exe",),
            ApplicationState.NOT_RUNNING,
        ),
        (
            ApplicationIdentifier.NOTEPAD,
            None,
            ApplicationState.UNKNOWN,
        ),
    ),
)
def test_windows_reader_maps_only_fixed_native_identities(
    application_id: ApplicationIdentifier,
    process_names: tuple[str, ...] | None,
    expected_state: ApplicationState,
) -> None:
    reader = WindowsApplicationStateReader(lambda: process_names, "win32")

    result = reader.read_status(
        ApplicationStatusRequest(application_id),
        make_context(),
    )

    assert result.application_id is application_id
    assert result.state is expected_state


def test_windows_reader_uses_fixed_tasklist_command_without_shell(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def run_process(
        command: tuple[str, ...],
        **arguments: object,
    ) -> subprocess.CompletedProcess[str]:
        captured["command"] = command
        captured.update(arguments)
        return subprocess.CompletedProcess(
            command,
            0,
            stdout='"notepad.exe","4321","Console","1","1,024 K"\n',
        )

    monkeypatch.setattr(
        "atreus.system.windows_application_state_reader.subprocess.run",
        run_process,
    )
    reader = WindowsApplicationStateReader(platform_name="win32")

    result = reader.read_status(
        ApplicationStatusRequest(ApplicationIdentifier.NOTEPAD),
        make_context(),
    )

    assert result.state is ApplicationState.RUNNING
    assert captured == {
        "command": ("tasklist.exe", "/FO", "CSV", "/NH"),
        "check": True,
        "capture_output": True,
        "text": True,
        "shell": False,
    }


def test_windows_reader_rejects_unmapped_spotify_without_inspection() -> None:
    call_count = 0

    def read_processes() -> tuple[str, ...]:
        nonlocal call_count
        call_count += 1
        return ("spotify.exe",)

    reader = WindowsApplicationStateReader(read_processes, "win32")

    with pytest.raises(UnsupportedSystemOperationError):
        reader.read_status(
            ApplicationStatusRequest(ApplicationIdentifier.SPOTIFY),
            make_context(),
        )

    assert call_count == 0


def test_windows_reader_translates_native_failure_without_private_detail() -> None:
    def fail_to_read() -> tuple[str, ...]:
        raise OSError("private process observation detail")

    reader = WindowsApplicationStateReader(fail_to_read, "win32")

    with pytest.raises(SystemNativeAdapterError) as captured:
        reader.read_status(
            ApplicationStatusRequest(ApplicationIdentifier.NOTEPAD),
            make_context(),
        )

    assert "private process observation detail" not in str(captured.value)


def test_runtime_sanitizes_status_native_failure() -> None:
    def fail_to_read() -> tuple[str, ...]:
        raise OSError("private process observation detail")

    runtime, _ = make_runtime(
        WindowsApplicationStateReader(fail_to_read, "win32")
    )

    result = runtime.invoke(make_invocation("notepad"))

    assert result.status is CapabilityExecutionStatus.FAILED
    assert result.error_code == "capability_execution_failed"
    assert "private process observation detail" not in repr(result)


def test_windows_reader_enforces_permission_cancellation_and_platform() -> None:
    request = ApplicationStatusRequest(ApplicationIdentifier.NOTEPAD)
    reader = WindowsApplicationStateReader(lambda: (), "win32")

    with pytest.raises(SystemPermissionDeniedError):
        reader.read_status(request, make_context(grants=()))
    with pytest.raises(SystemOperationCancelledError):
        reader.read_status(request, make_context(cancelled=True))
    with pytest.raises(UnsupportedSystemOperationError):
        WindowsApplicationStateReader(lambda: (), "linux").read_status(
            request,
            make_context(),
        )


def test_windows_reader_rejects_invalid_request_and_exposes_no_process_api() -> None:
    reader = WindowsApplicationStateReader(lambda: (), "win32")
    invalid = ApplicationStatusRequest("notepad")  # type: ignore[arg-type]

    with pytest.raises(InvalidSystemOperationError):
        reader.read_status(invalid, make_context())

    assert not hasattr(reader, "run")
    assert not hasattr(reader, "find_process")
    assert not hasattr(reader, "read_pid")
    assert not hasattr(reader, "shell")
