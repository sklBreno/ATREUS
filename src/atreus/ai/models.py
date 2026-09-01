"""Immutable AI availability contracts used by runtime consumers."""

from dataclasses import dataclass
from enum import StrEnum


class AIProviderAvailabilityState(StrEnum):
    """Identify the current availability of an AI Provider."""

    AVAILABLE = "AVAILABLE"
    DEGRADED = "DEGRADED"
    UNAVAILABLE = "UNAVAILABLE"


@dataclass(frozen=True, slots=True)
class AIProviderAvailability:
    """Describe provider availability without exposing provider internals."""

    state: AIProviderAvailabilityState
    reason_code: str | None = None
