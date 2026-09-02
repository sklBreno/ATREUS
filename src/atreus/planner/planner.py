"""Deterministic Version 1 Planner implementation."""

from datetime import UTC

from atreus.application.contracts import (
    deterministic_application_action,
    is_supported_application_action,
)
from atreus.application.models import ApplicationAction
from atreus.capability.contracts import (
    APPLICATION_ID_ARGUMENT,
    CapabilityArgument,
    CapabilityArguments,
)
from atreus.capability.models import (
    CapabilityAvailabilityState,
    CapabilityMetadata,
)
from atreus.interfaces.capability_registry import CapabilityCatalog
from atreus.interfaces.clock import Clock
from atreus.interfaces.event_bus import EventBus
from atreus.interfaces.planner import Planner
from atreus.planner.exceptions import (
    GoalNotPlannableError,
    InvalidCapabilityReferenceError,
    InvalidPlanningRequestError,
)
from atreus.planner.models import (
    Plan,
    PlanCreated,
    PlanningConstraints,
    PlanningRequest,
    PlanStep,
)


class DeterministicPlanner(Planner):
    """Build bounded sequential plans from explicit catalog metadata."""

    def __init__(
        self,
        capability_catalog: CapabilityCatalog,
        clock: Clock,
        event_bus: EventBus | None = None,
    ) -> None:
        """Initialize planning dependencies.

        Args:
            capability_catalog: Read-only capability metadata source.
            clock: Time source used to validate optional deadlines.
            event_bus: Event Bus used to publish successful plans.
        """
        self._capability_catalog = capability_catalog
        self._clock = clock
        self._event_bus = event_bus

    def create_plan(self, request: PlanningRequest) -> Plan:
        """Create a finite sequential plan without executing any step.

        Args:
            request: Immutable goal, context, and planning constraints.

        Returns:
            A validated immutable sequential plan.

        Raises:
            InvalidPlanningRequestError: If request or constraints are invalid.
            GoalNotPlannableError: If capability selection is ambiguous.
            InvalidCapabilityReferenceError: If selected metadata is unusable.
        """
        self._validate_request(request)
        selected_ids = self._select_capability_ids(
            request.goal,
            request.constraints,
            request.action,
        )
        ordered_metadata = self._resolve_capabilities(
            selected_ids,
            request.constraints,
        )
        if len(ordered_metadata) > request.constraints.maximum_steps:
            raise GoalNotPlannableError(
                "Plan exceeds the configured maximum step count."
            )

        step_ids = {
            metadata.identifier: f"step-{index}"
            for index, metadata in enumerate(ordered_metadata, start=1)
        }
        steps = tuple(
            PlanStep(
                step_id=step_ids[metadata.identifier],
                capability_id=metadata.identifier,
                arguments=self._capability_arguments(
                    request.goal,
                    metadata.identifier,
                    request.action,
                ),
                depends_on=tuple(
                    step_ids[dependency]
                    for dependency in metadata.dependencies
                ),
                requires_confirmation=False,
            )
            for metadata in ordered_metadata
        )
        required_permissions = tuple(
            sorted(
                {
                    permission
                    for metadata in ordered_metadata
                    for permission in metadata.permissions
                }
            )
        )
        plan = Plan(
            plan_id=request.planning_id,
            request_id=request.request_id,
            goal=request.goal.strip(),
            steps=steps,
            required_permissions=required_permissions,
            requires_confirmation=request.constraints.require_confirmation,
        )
        self._publish_plan(plan)
        return plan

    def _select_capability_ids(
        self,
        goal: str,
        constraints: PlanningConstraints,
        action: ApplicationAction | None,
    ) -> tuple[str, ...]:
        resolved_action = action or deterministic_application_action(goal)
        if resolved_action is not None:
            if not is_supported_application_action(resolved_action):
                raise GoalNotPlannableError(
                    "Application action is not supported."
                )
            allowed = constraints.allowed_capability_ids
            if (
                allowed is not None
                and resolved_action.capability_id not in allowed
            ):
                raise GoalNotPlannableError(
                    "Application action is outside the planning allowlist."
                )
            return (resolved_action.capability_id,)
        if constraints.allowed_capability_ids is not None:
            if not constraints.allowed_capability_ids:
                raise GoalNotPlannableError(
                    "Planning allowlist contains no capability identifiers."
                )
            return constraints.allowed_capability_ids

        available = self._capability_catalog.list_available()
        unblocked = tuple(
            metadata.identifier
            for metadata in available
            if metadata.identifier not in constraints.blocked_capability_ids
        )
        if len(unblocked) != 1:
            raise GoalNotPlannableError(
                "Planning requires one unambiguous capability or an allowlist."
            )
        return unblocked

    @staticmethod
    def _capability_arguments(
        goal: str,
        capability_id: str,
        action: ApplicationAction | None,
    ) -> CapabilityArguments:
        resolved_action = action or deterministic_application_action(goal)
        if resolved_action is not None:
            if capability_id != resolved_action.capability_id:
                raise InvalidCapabilityReferenceError(
                    "Application action capability does not match the plan step."
                )
            return (
                CapabilityArgument(
                    APPLICATION_ID_ARGUMENT,
                    resolved_action.application_id.value,
                ),
            )
        return ()

    def _resolve_capabilities(
        self,
        selected_ids: tuple[str, ...],
        constraints: PlanningConstraints,
    ) -> tuple[CapabilityMetadata, ...]:
        selected_set = set(selected_ids)
        ordered: list[CapabilityMetadata] = []
        resolved: set[str] = set()

        def resolve(identifier: str) -> None:
            if identifier in resolved:
                return
            if identifier in constraints.blocked_capability_ids:
                raise InvalidCapabilityReferenceError(
                    f"Capability '{identifier}' is blocked by planning constraints."
                )
            if (
                constraints.allowed_capability_ids is not None
                and identifier not in selected_set
            ):
                raise InvalidCapabilityReferenceError(
                    f"Capability '{identifier}' is outside the planning allowlist."
                )

            metadata = self._capability_catalog.get(identifier)
            if metadata is None:
                raise InvalidCapabilityReferenceError(
                    f"Capability '{identifier}' is not registered."
                )
            if (
                metadata.availability.state
                is not CapabilityAvailabilityState.AVAILABLE
            ):
                raise InvalidCapabilityReferenceError(
                    f"Capability '{identifier}' is not available."
                )
            for dependency in metadata.dependencies:
                resolve(dependency)
            resolved.add(identifier)
            ordered.append(metadata)

        for identifier in selected_ids:
            resolve(identifier)
        return tuple(ordered)

    def _validate_request(self, request: PlanningRequest) -> None:
        if not isinstance(request, PlanningRequest):
            raise InvalidPlanningRequestError(
                "Plan creation requires a PlanningRequest."
            )
        if not request.goal.strip():
            raise InvalidPlanningRequestError("Planning goal must be non-empty.")
        constraints = request.constraints
        if not isinstance(constraints, PlanningConstraints):
            raise InvalidPlanningRequestError(
                "Planning request contains invalid constraints."
            )
        if constraints.maximum_steps <= 0:
            raise InvalidPlanningRequestError(
                "Planning maximum_steps must be positive."
            )
        allowed = constraints.allowed_capability_ids
        if allowed is not None and len(allowed) != len(set(allowed)):
            raise InvalidPlanningRequestError(
                "Planning allowlist identifiers must be unique."
            )
        if len(constraints.blocked_capability_ids) != len(
            set(constraints.blocked_capability_ids)
        ):
            raise InvalidPlanningRequestError(
                "Planning blocklist identifiers must be unique."
            )
        if constraints.deadline is not None:
            deadline = constraints.deadline
            if deadline.tzinfo is None or deadline.utcoffset() is None:
                raise InvalidPlanningRequestError(
                    "Planning deadline must be timezone-aware."
                )
            if deadline.astimezone(UTC) <= self._clock.now().astimezone(UTC):
                raise InvalidPlanningRequestError(
                    "Planning deadline must be in the future."
                )

    def _publish_plan(self, plan: Plan) -> None:
        if self._event_bus is None:
            return
        self._event_bus.publish(
            PlanCreated(
                source="planner",
                correlation_id=plan.request_id,
                plan_id=plan.plan_id,
                request_id=plan.request_id,
                capability_ids=tuple(
                    step.capability_id for step in plan.steps
                ),
                step_count=len(plan.steps),
                requires_confirmation=plan.requires_confirmation,
            )
        )
