"""Immutable platform state contracts shared across runtime modules."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class OperationalState(StrEnum):
    """Identify the current operational state of the platform."""

    ACTIVE = "ACTIVE"
    PASSIVE = "PASSIVE"
    STANDBY = "STANDBY"


class PerformanceProfile(StrEnum):
    """Identify the active platform performance profile."""

    PERFORMANCE = "PERFORMANCE"
    BALANCED = "BALANCED"
    IDLE = "IDLE"


@dataclass(frozen=True, slots=True)
class PlatformStateSnapshot:
    """Represent immutable lifecycle and operating state owned by Core."""

    lifecycle_phase: str
    operational_state: OperationalState
    performance_profile: PerformanceProfile
    startup_at: datetime
    latest_state_change_at: datetime
