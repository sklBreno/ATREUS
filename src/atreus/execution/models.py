"""Immutable contracts owned by the Capability Runtime."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from atreus.capability.contracts import CapabilityArguments, CapabilityOutput
from atreus.context.models import ContextSnapshot
from atreus.events.models import Event
from atreus.interfaces.cancellation import CancellationSignal


class CapabilityExecutionStatus(StrEnum):
    """Identify one terminal capability invocation status."""

    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    TIMED_OUT = "TIMED_OUT"
    CANCELLED = "CANCELLED"


@dataclass(frozen=True, slots=True)
class CapabilityInvocation:
    """Represent one correlated capability invocation request."""

    invocation_id: UUID
    request_id: UUID
    plan_id: UUID | None
    step_id: str | None
    capability_id: str
    arguments: CapabilityArguments
    timeout_seconds: float | None
    permission_grants: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ExecutionContext:
    """Provide bounded runtime context to one capability implementation."""

    invocation_id: UUID
    request_id: UUID
    plan_id: UUID | None
    step_id: str | None
    context: ContextSnapshot
    permission_grants: tuple[str, ...]
    cancellation: CancellationSignal


@dataclass(frozen=True, slots=True)
class CapabilityExecutionResult:
    """Represent one immutable terminal capability execution result."""

    invocation_id: UUID
    capability_id: str
    status: CapabilityExecutionStatus
    output: CapabilityOutput | None
    error_code: str | None
    started_at: datetime
    completed_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class CapabilityExecutionStarted(Event):
    """Report the start of a validated capability invocation."""

    invocation_id: UUID
    request_id: UUID
    capability_id: str
    plan_id: UUID | None
    step_id: str | None


@dataclass(frozen=True, slots=True, kw_only=True)
class CapabilityExecutionCompleted(Event):
    """Report successful completion without exposing capability output."""

    invocation_id: UUID
    request_id: UUID
    capability_id: str
    plan_id: UUID | None
    step_id: str | None
    duration_seconds: float


@dataclass(frozen=True, slots=True, kw_only=True)
class CapabilityExecutionFailed(Event):
    """Report sanitized unsuccessful capability execution metadata."""

    invocation_id: UUID
    request_id: UUID
    capability_id: str
    plan_id: UUID | None
    step_id: str | None
    terminal_status: CapabilityExecutionStatus
    error_code: str
