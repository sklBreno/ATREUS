"""Behavior tests for the minimal controlled System Layer boundary."""

from dataclasses import FrozenInstanceError
from uuid import uuid4

import pytest

from atreus.shared.cancellation import StaticCancellationSignal
from atreus.system.exceptions import (
    InvalidSystemOperationError,
    SystemNativeAdapterError,
    SystemOperationCancelledError,
    SystemPermissionDeniedError,
    UnsupportedSystemOperationError,
)
from atreus.system.models import (
    APPLICATION_CONTROL_PERMISSION,
    ApplicationIdentifier,
    ApplicationLaunchRequest,
    MetricAvailabilityStatus,
    PowerSource,
    SystemOperationContext,
)
from atreus.system.system_information import UnavailableSystemInformationProvider
from atreus.system.windows_application_launcher import (
    WindowsApplicationLauncher,
)
from tests.support import NOW, FixedClock


def make_context(
    *,
    grants: tuple[str, ...] = ("system.metrics.read",),
    cancelled: bool = False,
) -> SystemOperationContext:
    """Create a controlled system operation context."""
    return SystemOperationContext(
        uuid4(),
        uuid4(),
        "system.snapshot",
        grants,
        StaticCancellationSignal(cancelled),
    )


def test_safe_provider_returns_normalized_unavailable_snapshot() -> None:
    provider = UnavailableSystemInformationProvider(FixedClock())

    snapshot = provider.snapshot(make_context())

    assert snapshot.metric_status is MetricAvailabilityStatus.UNAVAILABLE
    assert snapshot.power_source is PowerSource.UNKNOWN
    assert snapshot.cpu_utilization is None
    assert snapshot.observed_at == NOW
    with pytest.raises(FrozenInstanceError):
        snapshot.cpu_utilization = 1.0  # type: ignore[misc]


def test_system_layer_denies_missing_metrics_permission() -> None:
    provider = UnavailableSystemInformationProvider(FixedClock())

    with pytest.raises(SystemPermissionDeniedError):
        provider.snapshot(make_context(grants=()))


def test_system_layer_respects_pre_requested_cancellation() -> None:
    provider = UnavailableSystemInformationProvider(FixedClock())

    with pytest.raises(SystemOperationCancelledError):
        provider.snapshot(make_context(cancelled=True))


def test_system_information_boundary_has_no_arbitrary_execution() -> None:
    provider = UnavailableSystemInformationProvider(FixedClock())

    assert not hasattr(provider, "run")
    assert not hasattr(provider, "execute_command")
    assert not hasattr(provider, "shell")
    assert not hasattr(provider, "write_file")


@pytest.mark.parametrize(
    ("application_id", "expected_command"),
    (
        (ApplicationIdentifier.CALCULATOR, ("calc.exe",)),
        (ApplicationIdentifier.NOTEPAD, ("notepad.exe",)),
    ),
)
def test_windows_controller_launches_only_allowlisted_application_command(
    application_id: ApplicationIdentifier,
    expected_command: tuple[str, ...],
) -> None:
    commands: list[tuple[str, ...]] = []

    def start_process(command: tuple[str, ...]) -> int:
        commands.append(command)
        return 4321

    controller = WindowsApplicationLauncher(start_process, "win32")
    context = make_context(grants=(APPLICATION_CONTROL_PERMISSION,))

    instance = controller.launch(
        ApplicationLaunchRequest(application_id),
        context,
    )

    assert commands == [expected_command]
    assert instance.application_id is application_id
    assert instance.process_id == 4321


def test_windows_controller_normalizes_approved_identifier_without_mapping() -> None:
    commands: list[tuple[str, ...]] = []

    def start_process(command: tuple[str, ...]) -> int:
        commands.append(command)
        return 4321

    controller = WindowsApplicationLauncher(start_process, "win32")

    with pytest.raises(UnsupportedSystemOperationError) as captured:
        controller.launch(
            ApplicationLaunchRequest(ApplicationIdentifier.SPOTIFY),
            make_context(grants=(APPLICATION_CONTROL_PERMISSION,)),
        )

    assert "spotify" in str(captured.value)
    assert commands == []


def test_windows_controller_translates_native_launch_failure() -> None:
    def fail_to_start(command: tuple[str, ...]) -> int:
        raise OSError(f"private native failure for {command!r}")

    controller = WindowsApplicationLauncher(fail_to_start, "win32")

    with pytest.raises(SystemNativeAdapterError) as captured:
        controller.launch(
            ApplicationLaunchRequest(ApplicationIdentifier.CALCULATOR),
            make_context(grants=(APPLICATION_CONTROL_PERMISSION,)),
        )

    assert "private native failure" not in str(captured.value)


def test_windows_controller_enforces_permission_and_cancellation() -> None:
    controller = WindowsApplicationLauncher(lambda command: 1234, "win32")
    request = ApplicationLaunchRequest(ApplicationIdentifier.CALCULATOR)

    with pytest.raises(SystemPermissionDeniedError):
        controller.launch(request, make_context(grants=()))
    with pytest.raises(SystemOperationCancelledError):
        controller.launch(
            request,
            make_context(
                grants=(APPLICATION_CONTROL_PERMISSION,),
                cancelled=True,
            ),
        )


def test_windows_controller_rejects_invalid_and_unsupported_requests() -> None:
    controller = WindowsApplicationLauncher(lambda command: 1234, "win32")
    invalid_request = ApplicationLaunchRequest("terminal")  # type: ignore[arg-type]

    with pytest.raises(InvalidSystemOperationError):
        controller.launch(
            invalid_request,
            make_context(grants=(APPLICATION_CONTROL_PERMISSION,)),
        )
    with pytest.raises(UnsupportedSystemOperationError):
        WindowsApplicationLauncher(
            lambda command: 1234,
            "linux",
        ).launch(
            ApplicationLaunchRequest(ApplicationIdentifier.CALCULATOR),
            make_context(grants=(APPLICATION_CONTROL_PERMISSION,)),
        )


def test_application_launcher_exposes_no_arbitrary_execution_api() -> None:
    controller = WindowsApplicationLauncher(lambda command: 1234, "win32")

    assert not hasattr(controller, "run")
    assert not hasattr(controller, "execute_command")
    assert not hasattr(controller, "shell")
    assert not hasattr(controller, "start_process")
