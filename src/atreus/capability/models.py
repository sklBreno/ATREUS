"""Immutable contracts owned by the Capability Registry."""

from dataclasses import dataclass
from enum import StrEnum

from atreus.events.models import Event


class CapabilityAvailabilityState(StrEnum):
    """Identify the current eligibility of a capability."""

    AVAILABLE = "AVAILABLE"
    DISABLED = "DISABLED"
    UNAVAILABLE = "UNAVAILABLE"


@dataclass(frozen=True, slots=True)
class CapabilityAvailability:
    """Describe the current availability of a capability."""

    state: CapabilityAvailabilityState
    reason_code: str | None = None


@dataclass(frozen=True, slots=True)
class CapabilityMetadata:
    """Describe one capability without exposing executable behavior."""

    identifier: str
    name: str
    description: str
    permissions: tuple[str, ...]
    availability: CapabilityAvailability
    dependencies: tuple[str, ...]
    requires_ai: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class CapabilityRegistered(Event):
    """Report successful capability metadata registration."""

    capability_id: str
    availability_state: CapabilityAvailabilityState


@dataclass(frozen=True, slots=True, kw_only=True)
class CapabilityAvailabilityChanged(Event):
    """Report a change to effective capability availability."""

    capability_id: str
    previous_state: CapabilityAvailabilityState
    current_state: CapabilityAvailabilityState
    reason_code: str | None = None
