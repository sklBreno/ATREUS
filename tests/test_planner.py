"""Behavior tests for the deterministic Version 1 Planner."""

from dataclasses import FrozenInstanceError
from datetime import timedelta
from uuid import uuid4

import pytest

from atreus.capability.contracts import CapabilityArgument
from atreus.capability.models import (
    CapabilityAvailability,
    CapabilityAvailabilityState,
    CapabilityMetadata,
)
from atreus.capability.registry import InMemoryCapabilityRegistry
from atreus.context.models import (
    ContextSignalStatus,
    ContextSnapshot,
    ContextType,
)
from atreus.events.event_bus import InProcessEventBus
from atreus.memory.models import MemorySnapshot
from atreus.planner.exceptions import (
    GoalNotPlannableError,
    InvalidCapabilityReferenceError,
    InvalidPlanningRequestError,
)
from atreus.planner.models import (
    PlanCreated,
    PlanningConstraints,
    PlanningRequest,
)
from atreus.planner.planner import DeterministicPlanner
from tests.support import NOW, FixedClock


def make_metadata(
    identifier: str,
    *,
    permissions: tuple[str, ...] = (),
    dependencies: tuple[str, ...] = (),
    available: bool = True,
) -> CapabilityMetadata:
    """Create capability metadata for planner tests."""
    availability = (
        CapabilityAvailability(CapabilityAvailabilityState.AVAILABLE)
        if available
        else CapabilityAvailability(
            CapabilityAvailabilityState.DISABLED,
            "disabled_by_test",
        )
    )
    return CapabilityMetadata(
        identifier,
        identifier,
        f"Provide {identifier}.",
        permissions,
        availability,
        dependencies,
        False,
    )


def make_context() -> ContextSnapshot:
    """Create a deterministic context snapshot."""
    return ContextSnapshot(
        ContextType.WORKING,
        0.9,
        NOW,
        NOW,
        ContextSignalStatus.AVAILABLE,
    )


def make_request(
    *,
    allowed: tuple[str, ...] | None = None,
    blocked: tuple[str, ...] = (),
    maximum_steps: int = 4,
    require_confirmation: bool = False,
    goal: str = "Inspect system status",
) -> PlanningRequest:
    """Create a bounded planning request."""
    return PlanningRequest(
        uuid4(),
        uuid4(),
        goal,
        PlanningConstraints(
            allowed,
            blocked,
            maximum_steps,
            NOW + timedelta(minutes=1),
            require_confirmation,
        ),
        make_context(),
        MemorySnapshot(NOW, ()),
    )


def make_planner(
    registry: InMemoryCapabilityRegistry,
    event_bus: InProcessEventBus | None = None,
) -> DeterministicPlanner:
    """Create a deterministic Planner with a fixed clock."""
    return DeterministicPlanner(registry, FixedClock(), event_bus)


def test_single_available_capability_creates_one_step_plan() -> None:
    registry = InMemoryCapabilityRegistry()
    registry.register(make_metadata("system.snapshot"))
    request = make_request()

    plan = make_planner(registry).create_plan(request)

    assert plan.plan_id == request.planning_id
    assert plan.request_id == request.request_id
    assert tuple(step.capability_id for step in plan.steps) == (
        "system.snapshot",
    )
    assert plan.steps[0].arguments == ()


@pytest.mark.parametrize(
    ("goal", "application_id"),
    (
        ("open calculator", "calculator"),
        ("  OPEN   NOTEPAD!  ", "notepad"),
        ("Open Spotify.", "spotify"),
    ),
)
def test_open_application_plan_contains_allowlisted_argument(
    goal: str,
    application_id: str,
) -> None:
    registry = InMemoryCapabilityRegistry()
    registry.register(
        make_metadata(
            "application.open",
            permissions=("application.control",),
        )
    )
    registry.register(make_metadata("system.snapshot"))

    plan = make_planner(registry).create_plan(
        make_request(
            goal=goal,
            allowed=("application.open", "system.snapshot"),
            maximum_steps=1,
        )
    )

    assert len(plan.steps) == 1
    assert plan.steps[0].capability_id == "application.open"
    assert plan.steps[0].arguments == (
        CapabilityArgument("application_id", application_id),
    )
    assert plan.required_permissions == ("application.control",)


def test_open_application_fails_outside_planning_allowlist() -> None:
    registry = InMemoryCapabilityRegistry()
    registry.register(make_metadata("application.open"))

    with pytest.raises(GoalNotPlannableError):
        make_planner(registry).create_plan(
            make_request(
                goal="open calculator",
                allowed=("system.snapshot",),
            )
        )


def test_dependency_is_ordered_before_dependent_step() -> None:
    registry = InMemoryCapabilityRegistry()
    registry.register(make_metadata("system.snapshot"))
    registry.register(
        make_metadata(
            "system.report",
            dependencies=("system.snapshot",),
        )
    )
    request = make_request(allowed=("system.snapshot", "system.report"))

    plan = make_planner(registry).create_plan(request)

    assert tuple(step.capability_id for step in plan.steps) == (
        "system.snapshot",
        "system.report",
    )
    assert plan.steps[1].depends_on == (plan.steps[0].step_id,)


def test_permissions_are_deduplicated_and_sorted() -> None:
    registry = InMemoryCapabilityRegistry()
    registry.register(
        make_metadata(
            "system.snapshot",
            permissions=("system.metrics.read",),
        )
    )
    registry.register(
        make_metadata(
            "system.report",
            permissions=("report.read", "system.metrics.read"),
        )
    )

    plan = make_planner(registry).create_plan(
        make_request(allowed=("system.report", "system.snapshot"))
    )

    assert plan.required_permissions == (
        "report.read",
        "system.metrics.read",
    )


def test_complete_plan_confirmation_requirement_is_preserved() -> None:
    registry = InMemoryCapabilityRegistry()
    registry.register(make_metadata("system.snapshot"))

    plan = make_planner(registry).create_plan(
        make_request(require_confirmation=True)
    )

    assert plan.requires_confirmation is True


def test_empty_goal_is_invalid() -> None:
    registry = InMemoryCapabilityRegistry()
    registry.register(make_metadata("system.snapshot"))

    with pytest.raises(InvalidPlanningRequestError):
        make_planner(registry).create_plan(make_request(goal="  "))


def test_ambiguous_catalog_without_allowlist_fails_planning() -> None:
    registry = InMemoryCapabilityRegistry()
    registry.register(make_metadata("system.snapshot"))
    registry.register(make_metadata("system.report"))

    with pytest.raises(GoalNotPlannableError):
        make_planner(registry).create_plan(make_request())


def test_missing_and_unavailable_capabilities_fail_explicitly() -> None:
    registry = InMemoryCapabilityRegistry()
    registry.register(make_metadata("system.disabled", available=False))
    planner = make_planner(registry)

    with pytest.raises(InvalidCapabilityReferenceError):
        planner.create_plan(make_request(allowed=("system.missing",)))
    with pytest.raises(InvalidCapabilityReferenceError):
        planner.create_plan(make_request(allowed=("system.disabled",)))


def test_plan_respects_maximum_steps() -> None:
    registry = InMemoryCapabilityRegistry()
    registry.register(make_metadata("system.snapshot"))
    registry.register(make_metadata("system.report"))

    with pytest.raises(GoalNotPlannableError):
        make_planner(registry).create_plan(
            make_request(
                allowed=("system.snapshot", "system.report"),
                maximum_steps=1,
            )
        )


def test_plan_and_steps_are_immutable_and_deterministic() -> None:
    registry = InMemoryCapabilityRegistry()
    registry.register(make_metadata("system.snapshot"))
    request = make_request()
    planner = make_planner(registry)

    first = planner.create_plan(request)
    second = planner.create_plan(request)

    assert first == second
    with pytest.raises(FrozenInstanceError):
        first.goal = "changed"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        first.steps[0].capability_id = "changed"  # type: ignore[misc]
    assert not hasattr(first, "execute")


def test_plan_created_event_excludes_goal_and_arguments() -> None:
    event_bus = InProcessEventBus()
    events: list[PlanCreated] = []
    event_bus.subscribe(PlanCreated, events.append)
    registry = InMemoryCapabilityRegistry()
    registry.register(make_metadata("system.snapshot"))

    make_planner(registry, event_bus).create_plan(make_request())

    assert len(events) == 1
    assert events[0].capability_ids == ("system.snapshot",)
    assert not hasattr(events[0], "goal")
    assert not hasattr(events[0], "arguments")
