"""Behavior and integration tests for the Core Phase B pipeline."""

from uuid import uuid4

import pytest

from atreus.ai.exceptions import InvalidRequestInterpretationError
from atreus.ai.models import (
    REQUEST_INTERPRETER_SERVICE_ID,
    AIIntent,
    AIProviderAvailability,
    AIProviderAvailabilityState,
    RequestInterpretation,
)
from atreus.capability.open_application import OpenApplicationCapability
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
    Decision,
    DecisionInput,
    DecisionMade,
    DecisionOutcome,
    DecisionPolicy,
    PlatformBehaviorDecision,
    PlatformBehaviorDecisionInput,
    UserPolicy,
)
from atreus.events.event_bus import InProcessEventBus
from atreus.execution.models import (
    CapabilityExecutionCompleted,
    CapabilityExecutionResult,
    CapabilityExecutionStarted,
    CapabilityExecutionStatus,
    CapabilityInvocation,
)
from atreus.execution.runtime import InProcessCapabilityRuntime
from atreus.interfaces.application_controller import ApplicationController
from atreus.interfaces.capability import Capability
from atreus.interfaces.capability_runtime import CapabilityRuntime
from atreus.interfaces.context import ContextProvider
from atreus.interfaces.decision_engine import DecisionEngine
from atreus.interfaces.memory import MemorySnapshotProvider
from atreus.interfaces.planner import Planner
from atreus.interfaces.request_classifier import RequestClassifier
from atreus.interfaces.request_interpreter import RequestInterpreter
from atreus.interfaces.system_information import SystemInformationProvider
from atreus.memory.models import MemorySnapshot
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
    RecordingApplicationController,
    StaticAIAvailabilityProvider,
    StaticContextProvider,
    StaticMemorySnapshotProvider,
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
            ContextSignalStatus.AVAILABLE,
        )
    )


def build_core(
    *,
    classifier: RequestClassifier | None = None,
    planner: Planner | None = None,
    require_confirmation: bool = False,
    system_information: SystemInformationProvider | None = None,
    application_controller: ApplicationController | None = None,
    user_policy: UserPolicy | None = None,
    context_provider: ContextProvider | None = None,
    memory_snapshot_provider: MemorySnapshotProvider | None = None,
    request_interpreter: RequestInterpreter | None = None,
    decision_engine: DecisionEngine | None = None,
) -> tuple[Core, InProcessEventBus]:
    """Compose the complete controlled Phase B pipeline for tests."""
    event_bus = InProcessEventBus()
    clock = FixedClock()
    selected_context_provider = context_provider or make_context_provider()
    registry = InMemoryCapabilityRegistry(event_bus)
    if application_controller is None:
        system_provider = (
            system_information or UnavailableSystemInformationProvider(clock)
        )
        capabilities = (SystemSnapshotCapability(system_provider),)
        default_permission_grants = ("system.metrics.read",)
        allowed_capability_ids = ("system.snapshot",)
    else:
        capabilities = (OpenApplicationCapability(application_controller),)
        default_permission_grants = ("application.control",)
        allowed_capability_ids = ("application.open",)
    runtime = InProcessCapabilityRuntime(
        registry,
        StaticAIAvailabilityProvider(
            AIProviderAvailability(AIProviderAvailabilityState.UNAVAILABLE)
        ),
        StaticCancellationSignal(),
        clock,
        event_bus,
    )
    runtime.load(capabilities)
    core = Core(
        event_bus=event_bus,
        request_classifier=(
            classifier or DeterministicRequestClassifier(event_bus)
        ),
        capability_catalog=registry,
        decision_engine=(
            decision_engine
            or DeterministicDecisionEngine(
                DecisionPolicy(0.5),
                event_bus,
            )
        ),
        planner=planner or DeterministicPlanner(registry, clock, event_bus),
        capability_runtime=runtime,
        context_provider=selected_context_provider,
        memory_snapshot_provider=(
            memory_snapshot_provider or StaticMemorySnapshotProvider()
        ),
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
                permission_grants=default_permission_grants,
                blocked_capability_ids=(),
                allow_interruption=True,
                allow_delegation=False,
            )
        ),
        planning_constraints=PlanningConstraints(
            allowed_capability_ids=allowed_capability_ids,
            blocked_capability_ids=(),
            maximum_steps=1,
            deadline=None,
            require_confirmation=require_confirmation,
        ),
        execution_timeout_seconds=None,
        request_interpreter=request_interpreter,
    )
    return core, event_bus


class RecordingRequestInterpreter(RequestInterpreter):
    """Return one configured interpretation while recording requests."""

    def __init__(self, error: Exception | None = None) -> None:
        """Initialize successful or failing interpretation behavior."""
        self._error = error
        self.requests: list[Request] = []

    def interpret(self, request: Request) -> RequestInterpretation:
        """Record and return a non-executable interpretation."""
        self.requests.append(request)
        if self._error is not None:
            raise self._error
        return RequestInterpretation(
            request.request_id,
            AIIntent.OPEN_APPLICATION,
            "application.open",
            "calculator",
            0.9,
        )


class RecordingTwoPhaseDecisionEngine(DecisionEngine):
    """Record both decision inputs for one bounded interpretation flow."""

    def __init__(self) -> None:
        """Initialize an empty input collection."""
        self.inputs: list[DecisionInput] = []

    def decide(self, decision_input: DecisionInput) -> Decision:
        """Delegate once and require confirmation after interpretation."""
        self.inputs.append(decision_input)
        if decision_input.interpretation is None:
            return Decision(
                decision_input.request.request_id,
                DecisionOutcome.DELEGATE,
                REQUEST_INTERPRETER_SERVICE_ID,
                "bounded_request_interpretation_required",
            )
        return Decision(
            decision_input.request.request_id,
            DecisionOutcome.ASK_FOR_CONFIRMATION,
            "application.open",
            "ai_interpretation_requires_confirmation",
        )

    def decide_platform_behavior(
        self,
        decision_input: PlatformBehaviorDecisionInput,
    ) -> PlatformBehaviorDecision:
        """Reject platform evaluation outside this test boundary."""
        raise AssertionError("Platform behavior evaluation is not expected.")


class RecordingDecisionEngine(DecisionEngine):
    """Record request decision inputs and request deterministic planning."""

    def __init__(self) -> None:
        """Initialize an empty input collection."""
        self.inputs: list[DecisionInput] = []

    def decide(self, decision_input: DecisionInput) -> Decision:
        """Record the input and request one planned execution."""
        self.inputs.append(decision_input)
        return Decision(
            decision_input.request.request_id,
            DecisionOutcome.REQUEST_PLANNING,
            "system.snapshot",
            "context_identity_test",
        )

    def decide_platform_behavior(
        self,
        decision_input: PlatformBehaviorDecisionInput,
    ) -> PlatformBehaviorDecision:
        """Reject platform evaluation outside this test boundary."""
        raise AssertionError("Platform behavior evaluation is not expected.")


class RecordingPlanner(Planner):
    """Record planning requests and return one deterministic step."""

    def __init__(self) -> None:
        """Initialize an empty request collection."""
        self.requests: list[PlanningRequest] = []

    def create_plan(self, request: PlanningRequest) -> Plan:
        """Record and return one correlated plan."""
        self.requests.append(request)
        return Plan(
            plan_id=request.planning_id,
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
            required_permissions=(),
            requires_confirmation=False,
        )


class RecordingCapabilityRuntime(CapabilityRuntime):
    """Record invocations without performing capability work."""

    def __init__(self) -> None:
        """Initialize an empty invocation collection."""
        self.invocations: list[CapabilityInvocation] = []

    def load(self, capabilities: tuple[Capability, ...]) -> None:
        """Accept no loading work for this orchestration double."""

    def invoke(
        self,
        invocation: CapabilityInvocation,
    ) -> CapabilityExecutionResult:
        """Record and return one successful terminal result."""
        self.invocations.append(invocation)
        return CapabilityExecutionResult(
            invocation_id=invocation.invocation_id,
            capability_id=invocation.capability_id,
            status=CapabilityExecutionStatus.SUCCEEDED,
            output=(),
            error_code=None,
            started_at=NOW,
            completed_at=NOW,
        )


def build_context_tracking_core(
    context_provider: ContextProvider,
    memory_snapshot_provider: MemorySnapshotProvider | None = None,
) -> tuple[
    Core,
    RecordingDecisionEngine,
    RecordingPlanner,
    RecordingCapabilityRuntime,
    InProcessEventBus,
]:
    """Compose a Core with recording context-consumer boundaries."""
    event_bus = InProcessEventBus()
    registry = InMemoryCapabilityRegistry(event_bus)
    decision_engine = RecordingDecisionEngine()
    planner = RecordingPlanner()
    runtime = RecordingCapabilityRuntime()
    core = Core(
        event_bus=event_bus,
        request_classifier=DeterministicRequestClassifier(event_bus),
        capability_catalog=registry,
        decision_engine=decision_engine,
        planner=planner,
        capability_runtime=runtime,
        context_provider=context_provider,
        memory_snapshot_provider=(
            memory_snapshot_provider or StaticMemorySnapshotProvider()
        ),
        platform_state=PlatformStateSnapshot(
            "RUNNING",
            OperationalState.ACTIVE,
            PerformanceProfile.BALANCED,
            NOW,
            NOW,
        ),
        user_policy=UserPolicy((), (), True, False),
        planning_constraints=PlanningConstraints(None, (), 1, None, False),
        execution_timeout_seconds=None,
    )
    return core, decision_engine, planner, runtime, event_bus


def test_core_reuses_one_context_instance_through_planned_invocation() -> None:
    snapshot = ContextSnapshot(
        ContextType.WORKING,
        0.9,
        NOW,
        NOW,
        ContextSignalStatus.AVAILABLE,
    )
    context_provider = StaticContextProvider(snapshot)
    core, decision_engine, planner, runtime, _ = build_context_tracking_core(
        context_provider
    )

    result = core.handle_request(make_request("Plan a system snapshot"))

    assert result.execution_results
    assert context_provider.call_count == 1
    assert decision_engine.inputs[0].context is snapshot
    assert planner.requests[0].context is snapshot
    assert runtime.invocations[0].context is snapshot


def test_core_reuses_one_memory_instance_through_decision_and_planning() -> None:
    memory = MemorySnapshot(NOW, ())
    memory_provider = StaticMemorySnapshotProvider(memory)
    core, decision_engine, planner, _, _ = build_context_tracking_core(
        make_context_provider(),
        memory_provider,
    )

    result = core.handle_request(make_request("Plan a system snapshot"))

    assert result.execution_results
    assert memory_provider.call_count == 1
    assert decision_engine.inputs[0].memory is memory
    assert planner.requests[0].memory is memory


class FailingMemorySnapshotProvider(MemorySnapshotProvider):
    """Raise one private structural Working Memory failure."""

    def snapshot(self) -> MemorySnapshot:
        """Raise before request decision or execution can begin."""
        raise RuntimeError("private working memory detail")


def test_memory_provider_failure_stops_pipeline_with_sanitized_event() -> None:
    core, decision_engine, planner, runtime, event_bus = (
        build_context_tracking_core(
            make_context_provider(),
            FailingMemorySnapshotProvider(),
        )
    )
    errors: list[ErrorOccurred] = []
    event_bus.subscribe(ErrorOccurred, errors.append)

    with pytest.raises(RuntimeError, match="private working memory detail"):
        core.handle_request(make_request())

    assert decision_engine.inputs == []
    assert planner.requests == []
    assert runtime.invocations == []
    assert len(errors) == 1
    assert errors[0].orchestration_step == "working_memory_snapshot"
    assert errors[0].error_type == "RuntimeError"
    assert "private working memory detail" not in repr(errors[0])


class FailingContextProvider(ContextProvider):
    """Raise one private structural context failure."""

    def current_context(self) -> ContextSnapshot:
        """Raise before request decision or execution can begin."""
        raise RuntimeError("private context provider detail")


def test_context_provider_failure_stops_pipeline_with_sanitized_event() -> None:
    core, decision_engine, planner, runtime, event_bus = (
        build_context_tracking_core(FailingContextProvider())
    )
    errors: list[ErrorOccurred] = []
    event_bus.subscribe(ErrorOccurred, errors.append)

    with pytest.raises(RuntimeError, match="private context provider detail"):
        core.handle_request(make_request())

    assert decision_engine.inputs == []
    assert planner.requests == []
    assert runtime.invocations == []
    assert len(errors) == 1
    assert errors[0].orchestration_step == "context_snapshot"
    assert errors[0].error_type == "RuntimeError"
    assert "private context provider detail" not in repr(errors[0])


@pytest.mark.parametrize(
    "snapshot",
    (
        ContextSnapshot(
            ContextType.UNKNOWN,
            0.0,
            NOW,
            NOW,
            ContextSignalStatus.UNAVAILABLE,
        ),
        ContextSnapshot(
            ContextType.WORKING,
            0.5,
            NOW,
            NOW,
            ContextSignalStatus.DEGRADED,
        ),
    ),
)
def test_non_available_context_does_not_block_current_execution(
    snapshot: ContextSnapshot,
) -> None:
    context_provider = StaticContextProvider(snapshot)
    core, _ = build_core(context_provider=context_provider)

    result = core.handle_request(make_request())

    assert result.execution_results[0].status is CapabilityExecutionStatus.SUCCEEDED
    assert context_provider.call_count == 1


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


@pytest.mark.parametrize("application_id", ("calculator", "notepad", "spotify"))
def test_core_opens_application_through_complete_controlled_pipeline(
    application_id: str,
) -> None:
    controller = RecordingApplicationController(process_id=2468)
    core, _ = build_core(application_controller=controller)

    result = core.handle_request(make_request(f"open {application_id}"))

    assert result.classification.request_type is RequestType.COMMAND
    assert result.decision.outcome is DecisionOutcome.REQUEST_PLANNING
    assert result.decision.target == "application.open"
    assert result.plan is not None
    assert len(result.plan.steps) == 1
    assert result.plan.steps[0].capability_id == "application.open"
    assert tuple(
        (argument.name, argument.value)
        for argument in result.plan.steps[0].arguments
    ) == (("application_id", application_id),)
    assert len(result.execution_results) == 1
    assert result.execution_results[0].status is CapabilityExecutionStatus.SUCCEEDED
    assert len(controller.calls) == 1


@pytest.mark.parametrize(
    "content",
    (
        "open calculator && shutdown",
        "open notepad && calc",
        "open spotify && anything",
        "open calculator please run shutdown",
        "shutdown computer",
        "arbitrary text",
    ),
)
def test_core_rejects_unrelated_desktop_commands(content: str) -> None:
    controller = RecordingApplicationController()
    core, _ = build_core(application_controller=controller)

    result = core.handle_request(make_request(content))

    assert result.decision.outcome is DecisionOutcome.ASK_FOR_CONFIRMATION
    assert result.plan is None
    assert result.execution_results == ()
    assert controller.calls == []


def test_core_uses_one_interpretation_and_second_decision_without_execution() -> None:
    controller = RecordingApplicationController()
    interpreter = RecordingRequestInterpreter()
    context_provider = make_context_provider()
    memory_provider = StaticMemorySnapshotProvider()
    core, event_bus = build_core(
        application_controller=controller,
        context_provider=context_provider,
        memory_snapshot_provider=memory_provider,
        request_interpreter=interpreter,
        user_policy=UserPolicy(
            ("application.control",),
            (),
            True,
            True,
            REQUEST_INTERPRETER_SERVICE_ID,
        ),
    )
    decisions: list[DecisionMade] = []
    event_bus.subscribe(DecisionMade, decisions.append)

    result = core.handle_request(make_request("Please open calculator for me"))

    assert len(interpreter.requests) == 1
    assert len(decisions) == 2
    assert decisions[0].outcome is DecisionOutcome.DELEGATE
    assert decisions[1].outcome is DecisionOutcome.ASK_FOR_CONFIRMATION
    assert result.decision.outcome is DecisionOutcome.ASK_FOR_CONFIRMATION
    assert result.plan is None
    assert result.execution_results == ()
    assert controller.calls == []
    assert context_provider.call_count == 1
    assert memory_provider.call_count == 1


def test_core_reuses_context_and_memory_across_both_decisions() -> None:
    interpreter = RecordingRequestInterpreter()
    decision_engine = RecordingTwoPhaseDecisionEngine()
    context_provider = make_context_provider()
    memory_provider = StaticMemorySnapshotProvider()
    core, _ = build_core(
        application_controller=RecordingApplicationController(),
        context_provider=context_provider,
        memory_snapshot_provider=memory_provider,
        request_interpreter=interpreter,
        decision_engine=decision_engine,
    )

    result = core.handle_request(make_request("Please open calculator for me"))

    assert result.decision.outcome is DecisionOutcome.ASK_FOR_CONFIRMATION
    assert len(decision_engine.inputs) == 2
    assert decision_engine.inputs[0].context is decision_engine.inputs[1].context
    assert decision_engine.inputs[0].memory is decision_engine.inputs[1].memory
    assert decision_engine.inputs[0].interpretation is None
    assert decision_engine.inputs[1].interpretation is not None
    assert context_provider.call_count == 1
    assert memory_provider.call_count == 1
    assert len(interpreter.requests) == 1


@pytest.mark.parametrize("content", ("open calculator", "open notepad"))
def test_core_deterministic_application_commands_make_zero_ai_calls(
    content: str,
) -> None:
    controller = RecordingApplicationController()
    interpreter = RecordingRequestInterpreter()
    core, _ = build_core(
        application_controller=controller,
        request_interpreter=interpreter,
        user_policy=UserPolicy(
            ("application.control",),
            (),
            True,
            True,
            REQUEST_INTERPRETER_SERVICE_ID,
        ),
    )

    result = core.handle_request(make_request(content))

    assert result.execution_results[0].status is CapabilityExecutionStatus.SUCCEEDED
    assert interpreter.requests == []


def test_interpreter_failure_is_sanitized_and_never_executes() -> None:
    private_detail = "private provider response and secret"
    interpreter = RecordingRequestInterpreter(
        InvalidRequestInterpretationError(private_detail)
    )
    controller = RecordingApplicationController()
    core, event_bus = build_core(
        application_controller=controller,
        request_interpreter=interpreter,
        user_policy=UserPolicy(
            ("application.control",),
            (),
            True,
            True,
            REQUEST_INTERPRETER_SERVICE_ID,
        ),
    )
    errors: list[ErrorOccurred] = []
    event_bus.subscribe(ErrorOccurred, errors.append)

    result = core.handle_request(make_request("Please open calculator for me"))

    assert result.decision.outcome is DecisionOutcome.DELEGATE
    assert result.execution_results == ()
    assert controller.calls == []
    assert len(errors) == 1
    assert errors[0].error_type == "InvalidRequestInterpretationError"
    assert private_detail not in repr(errors[0])


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
