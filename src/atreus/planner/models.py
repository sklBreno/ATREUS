"""Immutable contracts owned by the Planner."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from atreus.capability.contracts import CapabilityArguments
from atreus.context.models import ContextSnapshot
from atreus.events.models import Event


@dataclass(frozen=True, slots=True)
class PlanningConstraints:
    """Bound capability selection and Version 1 plan generation."""

    allowed_capability_ids: tuple[str, ...] | None
    blocked_capability_ids: tuple[str, ...]
    maximum_steps: int
    deadline: datetime | None
    require_confirmation: bool


@dataclass(frozen=True, slots=True)
class PlanningRequest:
    """Represent one correlated high-level goal submitted for planning."""

    planning_id: UUID
    request_id: UUID
    goal: str
    constraints: PlanningConstraints
    context: ContextSnapshot


@dataclass(frozen=True, slots=True)
class PlanStep:
    """Represent one immutable sequential capability invocation proposal."""

    step_id: str
    capability_id: str
    arguments: CapabilityArguments
    depends_on: tuple[str, ...]
    requires_confirmation: bool


@dataclass(frozen=True, slots=True)
class Plan:
    """Represent a finite validated sequence of capability steps."""

    plan_id: UUID
    request_id: UUID
    goal: str
    steps: tuple[PlanStep, ...]
    required_permissions: tuple[str, ...]
    requires_confirmation: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class PlanCreated(Event):
    """Report creation of a valid plan without goals or arguments."""

    plan_id: UUID
    request_id: UUID
    capability_ids: tuple[str, ...]
    step_count: int
    requires_confirmation: bool
