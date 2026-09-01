"""Immutable contracts used by the ATREUS Event Bus."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4


@dataclass(frozen=True, slots=True, kw_only=True)
class Event:
    """Represent an immutable fact published by an ATREUS module."""

    source: str
    event_id: UUID = field(default_factory=uuid4)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    correlation_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class Subscription:
    """Identify exactly one Event Bus registration."""

    identifier: UUID = field(default_factory=uuid4)


@dataclass(frozen=True, slots=True)
class SubscriberFailure:
    """Describe one isolated subscriber failure without exposing an exception."""

    subscription: Subscription
    error_type: str
    description: str


@dataclass(frozen=True, slots=True)
class PublicationResult:
    """Summarize deterministic delivery for one event publication."""

    delivered_count: int = 0
    failures: tuple[SubscriberFailure, ...] = ()
