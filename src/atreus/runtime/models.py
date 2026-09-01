"""Immutable runtime lifecycle contracts for the foreground ATREUS host."""

from dataclasses import dataclass
from enum import StrEnum

from atreus.events.models import Event


class RuntimeLifecycleState(StrEnum):
    """Identify the current lifecycle state of the local Runtime Host."""

    CREATED = "CREATED"
    STARTING = "STARTING"
    RUNNING = "RUNNING"
    STOPPING = "STOPPING"
    STOPPED = "STOPPED"
    FAILED = "FAILED"


@dataclass(frozen=True, slots=True, kw_only=True)
class RuntimeStarting(Event):
    """Report that the Runtime Host entered startup."""

    lifecycle_state: RuntimeLifecycleState


@dataclass(frozen=True, slots=True, kw_only=True)
class RuntimeStarted(Event):
    """Report that the Runtime Host can accept foreground requests."""

    lifecycle_state: RuntimeLifecycleState


@dataclass(frozen=True, slots=True, kw_only=True)
class RuntimeStopping(Event):
    """Report that the Runtime Host began deterministic shutdown."""

    lifecycle_state: RuntimeLifecycleState


@dataclass(frozen=True, slots=True, kw_only=True)
class RuntimeStopped(Event):
    """Report that the Runtime Host completed shutdown."""

    lifecycle_state: RuntimeLifecycleState


@dataclass(frozen=True, slots=True, kw_only=True)
class RuntimeFailed(Event):
    """Report a sanitized fatal Runtime Host lifecycle failure."""

    lifecycle_state: RuntimeLifecycleState
    failure_stage: str
    error_type: str
