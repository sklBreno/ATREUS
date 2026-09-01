"""Immutable context contracts shared with context-aware consumers."""

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum

from atreus.context.exceptions import InvalidContextSnapshotError


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

    AVAILABLE = "AVAILABLE"
    DEGRADED = "DEGRADED"
    UNAVAILABLE = "UNAVAILABLE"


@dataclass(frozen=True, slots=True)
class ContextSnapshot:
    """Represent validated ephemeral context without exposing raw signals."""

    context_type: ContextType
    confidence: float
    started_at: datetime
    evaluated_at: datetime
    signal_status: ContextSignalStatus

    def __post_init__(self) -> None:
        """Validate invariants and normalize timestamps to UTC.

        Raises:
            InvalidContextSnapshotError: If the snapshot is inconsistent.
        """
        if not 0.0 <= self.confidence <= 1.0:
            raise InvalidContextSnapshotError(
                "Context confidence must be between 0.0 and 1.0."
            )

        started_at = self._normalize_timestamp(self.started_at, "started_at")
        evaluated_at = self._normalize_timestamp(
            self.evaluated_at,
            "evaluated_at",
        )
        if started_at > evaluated_at:
            raise InvalidContextSnapshotError(
                "Context start time must not follow its evaluation time."
            )
        if self.signal_status is ContextSignalStatus.UNAVAILABLE and (
            self.context_type is not ContextType.UNKNOWN
            or self.confidence != 0.0
        ):
            raise InvalidContextSnapshotError(
                "Unavailable context must be unknown with zero confidence."
            )

        object.__setattr__(self, "started_at", started_at)
        object.__setattr__(self, "evaluated_at", evaluated_at)

    @staticmethod
    def _normalize_timestamp(timestamp: datetime, field_name: str) -> datetime:
        if timestamp.tzinfo is None or timestamp.utcoffset() is None:
            raise InvalidContextSnapshotError(
                f"Context {field_name} must be timezone-aware."
            )
        return timestamp.astimezone(UTC)
