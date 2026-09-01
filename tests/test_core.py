"""Behavior and integration tests for the Core Phase B pipeline."""

from uuid import uuid4

import pytest

from atreus.ai.models import (
    AIProviderAvailability,
    AIProviderAvailabilityState,
)
from atreus.capability.registry import InMemoryCapabilityRegistry
from atreus.capability.system_snapshot import SystemSnapshotCapability
from atreus.context.models import (
    ContextSignalStatus,
    ContextSnapshot,
    ContextType,
)
from atreus.core.core import Core
from atreus.core.exceptions import (
    InconsistentClassificationError,
    InconsistentPlanError,
)
from atreus.core.models import ErrorOccurred, RequestCompleted, RequestReceived
from atreus.decision.decision_engine import DeterministicDecisionEngine
from atreus.decision.models import (
    DecisionMade,
    DecisionOutcome,
    DecisionPolicy,
    UserPolicy,
)
from atreus.events.event_bus import InProcessEventBus
from atreus.execution.models import (
    CapabilityExecutionCompleted,
    CapabilityExecutionStarted,
    CapabilityExecutionStatus,
)
from atreus.execution.runtime import InProcessCapabilityRuntime
from atreus.interfaces.planner import Planner
from atreus.interfaces.request_classifier import RequestClassifier
from atreus.interfaces.system_information import SystemInformationProvider
from atreus.planner.models import (
    Plan,
    PlanCreated,
    PlanningConstraints,
    PlanningRequest,
    PlanStep,
)
from atreus.planner.planner import DeterministicPlanner
from atreus.request_classifier.classifier import DeterministicRequestClassifier
from atreus.request_classifier.models import (
    ClassifiedRequest,
    RequestClassified,
    RequestType,
)
from atreus.shared.cancellation import StaticCancellationSignal
from atreus.shared.platform import (
    OperationalState,
    PerformanceProfile,
    PlatformStateSnapshot,
)
from atreus.shared.request import Request
from atreus.system.models import SystemOperationContext, SystemSnapshot
from atreus.system.system_information import UnavailableSystemInformationProvider
from tests.support import (
    NOW,
    FixedClock,
    StaticAIAvailabilityProvider,
    StaticContextProvider,
)


def make_request(content: str = "Run system.snapshot") -> Request:
    """Create a normalized request for Core tests."""
    return Request(uuid4(), content, "text", NOW)


def make_context_provider() -> StaticContextProvider:
    """Create a stable context provider for the complete pipeline."""
    return StaticContextProvider(
        ContextSnapshot(
            ContextType.WORKING,
            0.9,
            NOW,
            NOW,
            ContextSignalStatus.COMPLETE,
        )
    )


def build_core(
    *,
    classifier: RequestClassifier | None = None,
    planner: Planner | None = None,
    require_confirmation: bool = False,
    system_information: SystemInformationProvider | None = None,
    user_policy: UserPolicy | None = None,
) -> tuple[Core, InProcessEventBus]:
    """Compose the complete controlled Phase B pipeline for tests."""
    event_bus = InProcessEventBus()
    clock = FixedClock()
    context_provider = make_context_provider()
    registry = InMemoryCapabilityRegistry(event_bus)
    system_provider = system_information or UnavailableSystemInformationProvider(
        clock
    )
    runtime = InProcessCapabilityRuntime(
        registry,
        context_provider,
        StaticAIAvailabilityProvider(
            AIProviderAvailability(AIProviderAvailabilityState.UNAVAILABLE)
        ),
        StaticCancellationSignal(),
        clock,
        event_bus,
    )
    runtime.load((SystemSnapshotCapability(system_provider),))
    core = Core(
        event_bus=event_bus,
        request_classifier=(
            classifier or DeterministicRequestClassifier(event_bus)
        ),
        capability_catalog=registry,
        decision_engine=DeterministicDecisionEngine(
            DecisionPolicy(0.5),
            event_bus,
        ),
        planner=planner or DeterministicPlanner(registry, clock, event_bus),
        capability_runtime=runtime,
        context_provider=context_provider,
        platform_state=PlatformStateSnapshot(
            "RUNNING",
            OperationalState.ACTIVE,
            PerformanceProfile.BALANCED,
            NOW,
            NOW,
        ),
        user_policy=(
            user_policy
            or UserPolicy(
                permission_grants=("system.metrics.read",),
                blocked_capability_ids=(),
                allow_interruption=True,
                allow_delegation=False,
            )
        ),
        planning_constraints=PlanningConstraints(
            allowed_capability_ids=("system.snapshot",),
            blocked_capability_ids=(),
            maximum_steps=1,
            deadline=None,
            require_confirmation=require_confirmation,
        ),
        execution_timeout_seconds=None,
    )
    return core, event_bus


def test_core_executes_direct_decision_only_through_runtime() -> None:
    core, _ = build_core()
    request = make_request()

    result = core.handle_request(request)

    assert result.request_id == request.request_id
    assert result.classification.request_type is RequestType.COMMAND
    assert result.decision.outcome is DecisionOutcome.EXECUTE
    assert result.decision.target == "system.snapshot"
    assert result.plan is None
    assert len(result.execution_results) == 1
    assert result.execution_results[0].status is CapabilityExecutionStatus.SUCCEEDED


def test_core_plans_and_executes_high_level_intention_step_by_step() -> None:
    core, _ = build_core()

    result = core.handle_request(make_request("I want to run system.snapshot"))

    assert result.decision.outcome is DecisionOutcome.REQUEST_PLANNING
    assert result.plan is not None
    assert tuple(step.capability_id for step in result.plan.steps) == (
        "system.snapshot",
    )
    assert len(result.execution_results) == 1
    assert result.execution_results[0].status is CapabilityExecutionStatus.SUCCEEDED


def test_core_returns_low_confidence_outcome_without_execution() -> None:
    core, _ = build_core()

    result = core.handle_request(make_request("The weekly overview"))

    assert result.decision.outcome is DecisionOutcome.ASK_FOR_CONFIRMATION
    assert result.plan is None
    assert result.execution_results == ()


def test_core_does_not_execute_unrelated_command() -> None:
    core, _ = build_core()

    result = core.handle_request(make_request("Open calculator"))

    assert result.decision.outcome is DecisionOutcome.ASK_FOR_CONFIRMATION
    assert result.decision.target is None
    assert result.execution_results == ()


@pytest.mark.parametrize(
    ("content", "user_policy", "expected_outcome"),
    [
        (
            "What is system status?",
            UserPolicy(("system.metrics.read",), (), True, False),
            DecisionOutcome.SUGGEST,
        ),
        (
            "Run system.snapshot",
            UserPolicy(
                ("system.metrics.read",),
                ("system.snapshot",),
                True,
                False,
            ),
            DecisionOutcome.IGNORE,
        ),
        (
            "What is system status?",
            UserPolicy(
                ("system.metrics.read",),
                (),
                True,
                True,
                "ai.default",
            ),
            DecisionOutcome.DELEGATE,
        ),
    ],
)
def test_core_returns_non_execution_outcomes_without_invocation(
    content: str,
    user_policy: UserPolicy,
    expected_outcome: DecisionOutcome,
) -> None:
    core, _ = build_core(user_policy=user_policy)

    result = core.handle_request(make_request(content))

    assert result.decision.outcome is expected_outcome
    assert result.plan is None
    assert result.execution_results == ()


def test_core_preserves_plan_confirmation_without_execution() -> None:
    core, _ = build_core(require_confirmation=True)

    result = core.handle_request(make_request("I want to run system.snapshot"))

    assert result.plan is not None
    assert result.plan.requires_confirmation is True
    assert result.execution_results == ()


def test_core_pipeline_publishes_events_in_owned_flow_order() -> None:
    core, event_bus = build_core()
    event_order: list[str] = []
    for event_type in (
        RequestReceived,
        RequestClassified,
        DecisionMade,
        PlanCreated,
        CapabilityExecutionStarted,
        CapabilityExecutionCompleted,
        RequestCompleted,
    ):
        event_bus.subscribe(
            event_type,
            lambda event: event_order.append(type(event).__name__),
        )

    core.handle_request(make_request("I want to run system.snapshot"))

    assert event_order == [
        "RequestReceived",
        "RequestClassified",
        "DecisionMade",
        "PlanCreated",
        "CapabilityExecutionStarted",
        "CapabilityExecutionCompleted",
        "RequestCompleted",
    ]


def test_core_object_processes_multiple_requests_without_reconstruction() -> None:
    core, _ = build_core()

    first = core.handle_request(make_request())
    second = core.handle_request(make_request("The weekly overview"))

    assert first.request_id != second.request_id
    assert first.execution_results
    assert second.execution_results == ()


class MismatchedRequestClassifier(RequestClassifier):
    """Return an invalid classification identity for boundary testing."""

    def classify(self, request: Request) -> ClassifiedRequest:
        """Return a classification for a different request identifier."""
        return ClassifiedRequest(uuid4(), RequestType.COMMAND, 1.0)


def test_core_rejects_classification_for_different_request() -> None:
    core, event_bus = build_core(classifier=MismatchedRequestClassifier())
    errors: list[ErrorOccurred] = []
    event_bus.subscribe(ErrorOccurred, errors.append)

    with pytest.raises(InconsistentClassificationError):
        core.handle_request(make_request())

    assert len(errors) == 1
    assert errors[0].orchestration_step == "request_classification"


class MismatchedPlanPlanner(Planner):
    """Return a plan for a different planning operation."""

    def create_plan(self, request: PlanningRequest) -> Plan:
        """Return a structurally valid plan with the wrong plan identifier."""
        return Plan(
            plan_id=uuid4(),
            request_id=request.request_id,
            goal=request.goal,
            steps=(
                PlanStep(
                    step_id="step-1",
                    capability_id="system.snapshot",
                    arguments=(),
                    depends_on=(),
                    requires_confirmation=False,
                ),
            ),
            required_permissions=("system.metrics.read",),
            requires_confirmation=False,
        )


def test_core_rejects_plan_for_different_planning_operation() -> None:
    core, event_bus = build_core(planner=MismatchedPlanPlanner())
    errors: list[ErrorOccurred] = []
    event_bus.subscribe(ErrorOccurred, errors.append)

    with pytest.raises(InconsistentPlanError):
        core.handle_request(make_request("I want to run system.snapshot"))

    assert len(errors) == 1
    assert errors[0].orchestration_step == "planning"


class FailingSystemInformationProvider(SystemInformationProvider):
    """Raise a private provider error for Runtime isolation testing."""

    def snapshot(self, context: SystemOperationContext) -> SystemSnapshot:
        """Raise an implementation failure."""
        raise RuntimeError("private native detail")


def test_core_receives_controlled_execution_failure_from_runtime() -> None:
    core, _ = build_core(system_information=FailingSystemInformationProvider())

    result = core.handle_request(make_request())

    assert len(result.execution_results) == 1
    assert result.execution_results[0].status is CapabilityExecutionStatus.FAILED
    assert result.execution_results[0].error_code == "capability_execution_failed"
