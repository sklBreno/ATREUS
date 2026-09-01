"""Immutable structured logging contracts for ATREUS observability."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True, kw_only=True)
class StructuredLogRecord:
    """Represent one sanitized machine-readable observability record."""

    timestamp: datetime
    level: str
    event_type: str
    message: str
    correlation_id: UUID | None = None
    request_id: UUID | None = None
    capability_id: str | None = None
    decision_outcome: str | None = None
    execution_status: str | None = None
    reason_code: str | None = None
