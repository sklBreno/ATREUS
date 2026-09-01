"""Immutable context contracts shared with context-aware consumers."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class ContextType(StrEnum):
    """Identify one supported Version 1 user context."""

    WORKING = "WORKING"
    STUDYING = "STUDYING"
    GAMING = "GAMING"
    MEETING = "MEETING"
    ENTERTAINMENT = "ENTERTAINMENT"
    IDLE = "IDLE"
    UNKNOWN = "UNKNOWN"


class ContextSignalStatus(StrEnum):
    """Describe the availability of signals behind a context snapshot."""

    COMPLETE = "COMPLETE"
    DEGRADED = "DEGRADED"
    UNAVAILABLE = "UNAVAILABLE"


@dataclass(frozen=True, slots=True)
class ContextSnapshot:
    """Represent the current context without exposing raw system signals."""

    context_type: ContextType
    confidence: float
    started_at: datetime
    evaluated_at: datetime
    signal_status: ContextSignalStatus
