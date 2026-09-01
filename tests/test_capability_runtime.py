"""Behavior tests for the synchronous Capability Runtime."""

from dataclasses import FrozenInstanceError
from uuid import uuid4

import pytest

from atreus.ai.models import (
    AIProviderAvailability,
    AIProviderAvailabilityState,
)
from atreus.capability.exceptions import RegistrySealedError
from atreus.capability.models import (
    CapabilityAvailability,
    CapabilityAvailabilityState,
    CapabilityMetadata,
)
from atreus.capability.registry import InMemoryCapabilityRegistry
from atreus.context.models import (
    ContextSignalStatus,
    ContextSnapshot,
    ContextType,
)
from atreus.events.event_bus import InProcessEventBus
from atreus.execution.exceptions import (
    CapabilityAIUnavailableError,
    DuplicateCapabilityImplementationError,
    InvalidCapabilityInvocationError,
    MissingCapabilityPermissionsError,
    UnavailableRuntimeCapabilityError,
    UnknownRuntimeCapabilityError,
    UnsupportedExecutionDeadlineError,
)
from atreus.execution.models import (
    CapabilityExecutionCompleted,
    CapabilityExecutionFailed,
    CapabilityExecutionStarted,
    CapabilityExecutionStatus,
    CapabilityInvocation,
)
from atreus.execution.runtime import InProcessCapabilityRuntime
from atreus.shared.cancellation import StaticCancellationSignal
from tests.support import (
    NOW,
    SUCCESS_OUTPUT,
    FixedClock,
    RecordingCapability,
    StaticAIAvailabilityProvider,
)


def make_context() -> ContextSnapshot:
    """Create an available context snapshot for Runtime tests."""
    return ContextSnapshot(
        ContextType.WORKING,
        0.9,
        NOW,
        NOW,
        ContextSignalStatus.AVAILABLE,
    )


def make_metadata(
    identifier: str = "system.snapshot",
    *,
    permissions: tuple[str, ...] = (),
    dependencies: tuple[str, ...] = (),
    available: bool = True,
    requires_ai: bool = False,
) -> CapabilityMetadata:
    """Create capability metadata for Runtime tests."""
    availability = (
        CapabilityAvailability(CapabilityAvailabilityState.AVAILABLE)
        if available
        else CapabilityAvailability(
            CapabilityAvailabilityState.DISABLED,
            "disabled_by_test",
        )
    )
    return CapabilityMetadata(
        identifier,
        identifier,
        f"Provide {identifier}.",
        permissions,
        availability,
        dependencies,
        requires_ai,
    )


def make_invocation(
    capability_id: str = "system.snapshot",
    *,
    permission_grants: tuple[str, ...] = (),
    timeout_seconds: float | None = None,
    context: ContextSnapshot | None = None,
) -> CapabilityInvocation:
    """Create one immutable direct capability invocation."""
    return CapabilityInvocation(
        invocation_id=uuid4(),
        request_id=uuid4(),
        plan_id=None,
        step_id=None,
        capability_id=capability_id,
        arguments=(),
        context=context if context is not None else make_context(),
        timeout_seconds=timeout_seconds,
        permission_grants=permission_grants,
    )


def make_runtime(
    *,
    ai_state: AIProviderAvailabilityState = (
        AIProviderAvailabilityState.UNAVAILABLE
    ),
    cancellation: StaticCancellationSignal = StaticCancellationSignal(),
    clock: FixedClock = FixedClock(),
    event_bus: InProcessEventBus | None = None,
) -> tuple[InProcessCapabilityRuntime, InMemoryCapabilityRegistry]:
    """Create an unloaded Capability Runtime and its Registry."""
    registry = InMemoryCapabilityRegistry(event_bus)
    runtime = InProcessCapabilityRuntime(
        registry,
        StaticAIAvailabilityProvider(AIProviderAvailability(ai_state)),
        cancellation,
        clock,
        event_bus,
    )
    return runtime, registry


def test_load_registers_implementations_and_seals_registry() -> None:
    runtime, registry = make_runtime()
    capability = RecordingCapability(make_metadata())

    runtime.load((capability,))

    assert registry.get("system.snapshot") == capability.metadata
    with pytest.raises(RegistrySealedError):
        registry.register(make_metadata("system.other"))


def test_load_rejects_duplicate_implementation_identifiers() -> None:
    runtime, _ = make_runtime()
    first = RecordingCapability(make_metadata())
    second = RecordingCapability(make_metadata())

    with pytest.raises(DuplicateCapabilityImplementationError):
        runtime.load((first, second))


def test_successful_invocation_returns_immutable_output() -> None:
    runtime, _ = make_runtime()
    capability = RecordingCapability(make_metadata(), output=SUCCESS_OUTPUT)
    runtime.load((capability,))
    invocation = make_invocation()

    result = runtime.invoke(invocation)

    assert result.status is CapabilityExecutionStatus.SUCCEEDED
    assert result.output == SUCCESS_OUTPUT
    assert result.error_code is None
    assert len(capability.calls) == 1
    assert capability.calls[0][1].context is invocation.context
    with pytest.raises(FrozenInstanceError):
        result.status = CapabilityExecutionStatus.FAILED  # type: ignore[misc]


def test_unknown_capability_raises_before_execution() -> None:
    runtime, _ = make_runtime()
    capability = RecordingCapability(make_metadata())
    runtime.load((capability,))

    with pytest.raises(UnknownRuntimeCapabilityError):
        runtime.invoke(make_invocation("system.missing"))
    assert capability.calls == []


def test_unavailable_capability_is_not_executed() -> None:
    runtime, _ = make_runtime()
    capability = RecordingCapability(make_metadata(available=False))
    runtime.load((capability,))

    with pytest.raises(UnavailableRuntimeCapabilityError):
        runtime.invoke(make_invocation())
    assert capability.calls == []


def test_missing_permission_is_denied_before_execution() -> None:
    runtime, _ = make_runtime()
    capability = RecordingCapability(
        make_metadata(permissions=("system.metrics.read",))
    )
    runtime.load((capability,))

    with pytest.raises(MissingCapabilityPermissionsError):
        runtime.invoke(make_invocation())
    assert capability.calls == []


def test_ai_required_capability_is_denied_when_ai_is_unavailable() -> None:
    runtime, _ = make_runtime()
    capability = RecordingCapability(make_metadata(requires_ai=True))
    runtime.load((capability,))

    with pytest.raises(CapabilityAIUnavailableError):
        runtime.invoke(make_invocation())
    assert capability.calls == []


def test_capability_exception_is_isolated_as_failed_result() -> None:
    event_bus = InProcessEventBus()
    failed_events: list[CapabilityExecutionFailed] = []
    event_bus.subscribe(CapabilityExecutionFailed, failed_events.append)
    runtime, _ = make_runtime(event_bus=event_bus)
    capability = RecordingCapability(
        make_metadata(),
        error=RuntimeError("sensitive detail"),
    )
    runtime.load((capability,))

    result = runtime.invoke(make_invocation())

    assert result.status is CapabilityExecutionStatus.FAILED
    assert result.output is None
    assert result.error_code == "capability_execution_failed"
    assert len(failed_events) == 1
    assert not hasattr(failed_events[0], "exception")
    assert not hasattr(failed_events[0], "output")


def test_requested_deadline_is_rejected_before_execution() -> None:
    runtime, _ = make_runtime()
    capability = RecordingCapability(make_metadata(), output=SUCCESS_OUTPUT)
    runtime.load((capability,))

    with pytest.raises(UnsupportedExecutionDeadlineError):
        runtime.invoke(make_invocation(timeout_seconds=1.0))
    assert capability.calls == []


def test_pre_requested_cancellation_returns_cancelled_without_execution() -> None:
    runtime, _ = make_runtime(cancellation=StaticCancellationSignal(True))
    capability = RecordingCapability(make_metadata())
    runtime.load((capability,))

    result = runtime.invoke(make_invocation())

    assert result.status is CapabilityExecutionStatus.CANCELLED
    assert capability.calls == []


def test_invalid_timeout_is_rejected_before_execution() -> None:
    runtime, _ = make_runtime()
    capability = RecordingCapability(make_metadata())
    runtime.load((capability,))

    with pytest.raises(InvalidCapabilityInvocationError):
        runtime.invoke(make_invocation(timeout_seconds=0.0))
    assert capability.calls == []


def test_lifecycle_events_are_ordered_and_exclude_sensitive_values() -> None:
    event_bus = InProcessEventBus()
    lifecycle: list[object] = []
    event_bus.subscribe(CapabilityExecutionStarted, lifecycle.append)
    event_bus.subscribe(CapabilityExecutionCompleted, lifecycle.append)
    runtime, _ = make_runtime(event_bus=event_bus)
    capability = RecordingCapability(make_metadata(), output=SUCCESS_OUTPUT)
    runtime.load((capability,))

    runtime.invoke(make_invocation())

    assert [type(event) for event in lifecycle] == [
        CapabilityExecutionStarted,
        CapabilityExecutionCompleted,
    ]
    assert all(not hasattr(event, "arguments") for event in lifecycle)
    assert all(not hasattr(event, "permission_grants") for event in lifecycle)
    assert all(not hasattr(event, "output") for event in lifecycle)


def test_runtime_exposes_no_plan_or_bulk_execution_api() -> None:
    runtime, _ = make_runtime()

    assert not hasattr(runtime, "invoke_plan")
    assert not hasattr(runtime, "execute_all")
