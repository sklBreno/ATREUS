"""Immutable contracts owned by the Core orchestration boundary."""

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from atreus.capability.models import CapabilityMetadata
from atreus.events.models import Event
from atreus.request_classifier.models import ClassifiedRequest


class CoreRequestStatus(StrEnum):
    """Identify the controlled Phase A orchestration outcome."""

    DECISION_REQUIRED = "DECISION_REQUIRED"


@dataclass(frozen=True, slots=True, kw_only=True)
class RequestReceived(Event):
    """Report that Core accepted a normalized request."""

    request_id: UUID


@dataclass(frozen=True, slots=True)
class CoreRequestResult:
    """Represent the Phase A boundary before future decision processing."""

    request_id: UUID
    classification: ClassifiedRequest
    available_capabilities: tuple[CapabilityMetadata, ...]
    status: CoreRequestStatus
