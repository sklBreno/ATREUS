"""Tests for the controlled application-opening capability."""

from uuid import uuid4

import pytest

from atreus.ai.models import (
    AIProviderAvailability,
    AIProviderAvailabilityState,
)
from atreus.capability.contracts import (
    APPLICATION_ID_ARGUMENT,
    OPEN_APPLICATION_CAPABILITY_ID,
    CapabilityArgument,
)
from atreus.capability.open_application import OpenApplicationCapability
from atreus.capability.registry import InMemoryCapabilityRegistry
from atreus.context.models import (
    ContextSignalStatus,
    ContextSnapshot,
    ContextType,
)
from atreus.execution.models import CapabilityExecutionStatus, CapabilityInvocation
from atreus.execution.runtime import InProcessCapabilityRuntime
from atreus.interfaces.application_controller import ApplicationController
from atreus.shared.cancellation import StaticCancellationSignal
from atreus.system.models import (
    APPLICATION_CONTROL_PERMISSION,
    ApplicationIdentifier,
)
from atreus.system.windows_application_controller import (
    WindowsApplicationController,
)
from tests.support import (
    NOW,
    FixedClock,
    RecordingApplicationController,
    StaticAIAvailabilityProvider,
)


def make_runtime(
    controller: ApplicationController,
) -> tuple[InProcessCapabilityRuntime, InMemoryCapabilityRegistry]:
    """Create a Runtime loaded with the controlled application capability."""
    registry = InMemoryCapabilityRegistry()
    runtime = InProcessCapabilityRuntime(
        registry,
        StaticAIAvailabilityProvider(
            AIProviderAvailability(AIProviderAvailabilityState.UNAVAILABLE)
        ),
        StaticCancellationSignal(),
        FixedClock(),
    )
    runtime.load((OpenApplicationCapability(controller),))
    return runtime, registry


def make_invocation(application_id: str = "calculator") -> CapabilityInvocation:
    """Create one authorized application-opening invocation."""
    return CapabilityInvocation(
        invocation_id=uuid4(),
        request_id=uuid4(),
        plan_id=uuid4(),
        step_id="step-1",
        capability_id=OPEN_APPLICATION_CAPABILITY_ID,
        arguments=(CapabilityArgument(APPLICATION_ID_ARGUMENT, application_id),),
        context=ContextSnapshot(
            ContextType.WORKING,
            0.9,
            NOW,
            NOW,
            ContextSignalStatus.AVAILABLE,
        ),
        timeout_seconds=None,
        permission_grants=(APPLICATION_CONTROL_PERMISSION,),
    )


def test_runtime_loading_registers_open_application_capability() -> None:
    _, registry = make_runtime(RecordingApplicationController())

    metadata = registry.get(OPEN_APPLICATION_CAPABILITY_ID)

    assert metadata is not None
    assert metadata.permissions == (APPLICATION_CONTROL_PERMISSION,)
    assert metadata.requires_ai is False


@pytest.mark.parametrize(
    ("application_id", "expected_identifier"),
    (
        ("calculator", ApplicationIdentifier.CALCULATOR),
        ("notepad", ApplicationIdentifier.NOTEPAD),
        ("spotify", ApplicationIdentifier.SPOTIFY),
    ),
)
def test_runtime_invokes_open_application_through_system_boundary(
    application_id: str,
    expected_identifier: ApplicationIdentifier,
) -> None:
    controller = RecordingApplicationController(process_id=9876)
    runtime, _ = make_runtime(controller)

    result = runtime.invoke(make_invocation(application_id))

    assert result.status is CapabilityExecutionStatus.SUCCEEDED
    assert result.output is not None
    assert tuple((item.name, item.value) for item in result.output) == (
        ("application_id", application_id),
        ("process_id", 9876),
        ("status", "launched"),
    )
    assert len(controller.calls) == 1
    request, context = controller.calls[0]
    assert request.application_id is expected_identifier
    assert context.capability_id == OPEN_APPLICATION_CAPABILITY_ID
    assert context.permission_grants == (APPLICATION_CONTROL_PERMISSION,)


def test_runtime_isolates_unapproved_application_identifier() -> None:
    controller = RecordingApplicationController()
    runtime, _ = make_runtime(controller)

    result = runtime.invoke(make_invocation("terminal"))

    assert result.status is CapabilityExecutionStatus.FAILED
    assert result.error_code == "capability_execution_failed"
    assert controller.calls == []


def test_runtime_isolates_missing_windows_launch_mapping() -> None:
    commands: list[tuple[str, ...]] = []

    def start_process(command: tuple[str, ...]) -> int:
        commands.append(command)
        return 9876

    runtime, _ = make_runtime(
        WindowsApplicationController(start_process, "win32")
    )

    result = runtime.invoke(make_invocation("spotify"))

    assert result.status is CapabilityExecutionStatus.FAILED
    assert result.error_code == "capability_execution_failed"
    assert commands == []
