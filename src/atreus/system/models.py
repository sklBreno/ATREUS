"""Immutable platform-neutral contracts owned by the System Layer."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from atreus.interfaces.cancellation import CancellationSignal

SYSTEM_METRICS_READ_PERMISSION = "system.metrics.read"
APPLICATION_CONTROL_PERMISSION = "application.control"


class ApplicationIdentifier(StrEnum):
    """Identify one application approved for controlled system launch."""

    CALCULATOR = "calculator"
    NOTEPAD = "notepad"
    SPOTIFY = "spotify"


class MetricAvailabilityStatus(StrEnum):
    """Describe coverage of metrics in a system snapshot."""

    COMPLETE = "COMPLETE"
    DEGRADED = "DEGRADED"
    UNAVAILABLE = "UNAVAILABLE"


class PowerSource(StrEnum):
    """Identify the normalized source currently powering the system."""

    AC = "AC"
    BATTERY = "BATTERY"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class SystemOperationContext:
    """Carry correlation, grants, and cancellation to a system operation."""

    operation_id: UUID
    request_id: UUID | None
    capability_id: str
    permission_grants: tuple[str, ...]
    cancellation: CancellationSignal


@dataclass(frozen=True, slots=True)
class ApplicationLaunchRequest:
    """Request launch of one explicitly identified approved application."""

    application_id: ApplicationIdentifier


@dataclass(frozen=True, slots=True)
class ApplicationInstance:
    """Represent one normalized result of an application launch."""

    application_id: ApplicationIdentifier
    process_id: int


@dataclass(frozen=True, slots=True)
class SystemSnapshot:
    """Represent approved current system metrics without user content."""

    cpu_utilization: float | None
    gpu_utilization: float | None
    available_memory_bytes: int | None
    total_memory_bytes: int | None
    battery_level: float | None
    power_source: PowerSource
    observed_at: datetime
    metric_status: MetricAvailabilityStatus
