"""Immutable contracts owned by the Core orchestration boundary."""

from dataclasses import dataclass
from uuid import UUID

from atreus.decision.models import Decision, DecisionOutcome
from atreus.events.models import Event
from atreus.execution.models import (
    CapabilityExecutionResult,
    CapabilityExecutionStatus,
)
from atreus.planner.models import Plan
from atreus.request_classifier.models import ClassifiedRequest


@dataclass(frozen=True, slots=True, kw_only=True)
class RequestReceived(Event):
    """Report that Core accepted a normalized request."""

    request_id: UUID


@dataclass(frozen=True, slots=True, kw_only=True)
class RequestCompleted(Event):
    """Report completion of the currently supported request orchestration."""

    request_id: UUID
    decision_outcome: DecisionOutcome
    execution_statuses: tuple[CapabilityExecutionStatus, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class ErrorOccurred(Event):
    """Report a sanitized Core orchestration failure."""

    request_id: UUID
    orchestration_step: str
    error_type: str


@dataclass(frozen=True, slots=True)
class CoreRequestResult:
    """Represent one explicit Phase B request orchestration result."""

    request_id: UUID
    classification: ClassifiedRequest
    decision: Decision
    plan: Plan | None
    execution_results: tuple[CapabilityExecutionResult, ...]
