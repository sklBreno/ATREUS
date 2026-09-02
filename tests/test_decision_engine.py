"""Behavior tests for the deterministic Decision Engine."""

from dataclasses import FrozenInstanceError, replace
from datetime import timedelta
from uuid import uuid4

import pytest

from atreus.ai.models import (
    REQUEST_INTERPRETER_SERVICE_ID,
    AIIntent,
    RequestInterpretation,
)
from atreus.capability.models import (
    CapabilityAvailability,
    CapabilityAvailabilityState,
    CapabilityMetadata,
)
from atreus.confirmation.models import (
    ConfirmationAction,
    ConfirmationResolution,
    ConfirmationResolutionStatus,
    PendingConfirmation,
)
from atreus.context.models import (
    ContextSignalStatus,
    ContextSnapshot,
    ContextType,
)
from atreus.decision.decision_engine import DeterministicDecisionEngine
from atreus.decision.exceptions import InconsistentDecisionInputError
from atreus.decision.models import (
    DecisionInput,
    DecisionMade,
    DecisionOutcome,
    DecisionPolicy,
    PlatformBehaviorDecisionInput,
    PlatformBehaviorDecisionMade,
    PlatformBehaviorPolicy,
    UserPolicy,
)
from atreus.events.event_bus import InProcessEventBus
from atreus.interaction.models import InteractionLanguage
from atreus.memory.models import MemorySnapshot
from atreus.request_classifier.models import ClassifiedRequest, RequestType
from atreus.shared.platform import (
    OperationalState,
    PerformanceProfile,
    PlatformStateSnapshot,
)
from atreus.shared.request import Request
from atreus.system.models import ApplicationIdentifier
from tests.support import NOW


def make_metadata(
    identifier: str,
    *,
    permissions: tuple[str, ...] = (),
    available: bool = True,
) -> CapabilityMetadata:
    """Create available capability metadata for decision tests."""
    return CapabilityMetadata(
        identifier=identifier,
        name=identifier,
        description=f"Provide {identifier}.",
        permissions=permissions,
        availability=CapabilityAvailability(
            CapabilityAvailabilityState.AVAILABLE
            if available
            else CapabilityAvailabilityState.UNAVAILABLE
        ),
        dependencies=(),
        requires_ai=False,
    )


def make_input(
    *,
    content: str = "Run system.snapshot",
    request_type: RequestType = RequestType.COMMAND,
    confidence: float = 0.9,
    candidates: tuple[CapabilityMetadata, ...] = (),
    permission_grants: tuple[str, ...] = (),
    blocked_capability_ids: tuple[str, ...] = (),
    allow_interruption: bool = True,
    allow_delegation: bool = False,
    delegation_service_id: str | None = None,
    operational_state: OperationalState = OperationalState.ACTIVE,
    performance_profile: PerformanceProfile = PerformanceProfile.BALANCED,
    interpretation: RequestInterpretation | None = None,
    confirmation_status: ConfirmationResolutionStatus | None = None,
) -> DecisionInput:
    """Create one coherent immutable DecisionInput."""
    request_id = uuid4()
    request = Request(request_id, content, "text", NOW)
    confirmation: ConfirmationResolution | None = None
    if confirmation_status is not None:
        pending = (
            None
            if confirmation_status
            in {
                ConfirmationResolutionStatus.NOT_APPLICABLE,
                ConfirmationResolutionStatus.NO_PENDING,
            }
            else PendingConfirmation(
                uuid4(),
                uuid4(),
                ConfirmationAction(
                    AIIntent.OPEN_APPLICATION,
                    "application.open",
                    ApplicationIdentifier.CALCULATOR,
                ),
                InteractionLanguage.PT_BR,
                NOW - timedelta(seconds=1),
                (
                    NOW
                    if confirmation_status is ConfirmationResolutionStatus.EXPIRED
                    else NOW + timedelta(seconds=120)
                ),
            )
        )
        confirmation = ConfirmationResolution(
            request_id,
            confirmation_status,
            pending,
            NOW,
        )
    return DecisionInput(
        request=request,
        classification=ClassifiedRequest(
            request_id,
            request_type,
            confidence,
        ),
        context=ContextSnapshot(
            ContextType.WORKING,
            0.9,
            NOW,
            NOW,
            ContextSignalStatus.AVAILABLE,
        ),
        memory=MemorySnapshot(NOW, ()),
        platform_state=PlatformStateSnapshot(
            "RUNNING",
            operational_state,
            performance_profile,
            NOW,
            NOW,
        ),
        user_policy=UserPolicy(
            permission_grants,
            blocked_capability_ids,
            allow_interruption,
            allow_delegation,
            delegation_service_id,
        ),
        candidate_capabilities=candidates,
        interpretation=interpretation,
        confirmation=confirmation,
    )


def make_engine(
    event_bus: InProcessEventBus | None = None,
) -> DeterministicDecisionEngine:
    """Create a deterministic engine with an explicit confidence threshold."""
    return DeterministicDecisionEngine(DecisionPolicy(0.5), event_bus)


def test_command_with_one_permitted_capability_selects_execute() -> None:
    capability = make_metadata(
        "system.snapshot",
        permissions=("system.metrics.read",),
    )

    decision = make_engine().decide(
        make_input(
            candidates=(capability,),
            permission_grants=("system.metrics.read",),
        )
    )

    assert decision.outcome is DecisionOutcome.EXECUTE
    assert decision.target == "system.snapshot"


def test_unrelated_command_does_not_select_sole_available_capability() -> None:
    decision = make_engine().decide(
        make_input(
            content="Open calculator",
            candidates=(make_metadata("system.snapshot"),),
        )
    )

    assert decision.outcome is DecisionOutcome.ASK_FOR_CONFIRMATION
    assert decision.target is None
    assert decision.reason_code == "capability_target_not_established"


@pytest.mark.parametrize(
    "content",
    (
        "open calculator",
        "  OPEN   NOTEPAD!  ",
        "Open Spotify.",
    ),
)
def test_controlled_application_resolves_to_planning_target(content: str) -> None:
    decision = make_engine().decide(
        make_input(
            content=content,
            candidates=(
                make_metadata(
                    "application.open",
                    permissions=("application.control",),
                ),
            ),
            permission_grants=("application.control",),
        )
    )

    assert decision.outcome is DecisionOutcome.REQUEST_PLANNING
    assert decision.target == "application.open"
    assert decision.reason_code == "command_requires_explicit_plan"


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
def test_unrelated_commands_do_not_target_open_application(content: str) -> None:
    decision = make_engine().decide(
        make_input(
            content=content,
            candidates=(
                make_metadata(
                    "application.open",
                    permissions=("application.control",),
                ),
            ),
            permission_grants=("application.control",),
        )
    )

    assert decision.outcome is DecisionOutcome.ASK_FOR_CONFIRMATION
    assert decision.target is None


def test_low_confidence_requires_confirmation() -> None:
    decision = make_engine().decide(make_input(confidence=0.25))

    assert decision.outcome is DecisionOutcome.ASK_FOR_CONFIRMATION
    assert decision.target is None


def test_multiple_eligible_command_targets_require_confirmation() -> None:
    decision = make_engine().decide(
        make_input(
            candidates=(make_metadata("a"), make_metadata("b")),
        )
    )

    assert decision.outcome is DecisionOutcome.ASK_FOR_CONFIRMATION


@pytest.mark.parametrize("request_type", [RequestType.INTENTION, RequestType.TASK])
def test_high_level_requests_request_planning(request_type: RequestType) -> None:
    decision = make_engine().decide(
        make_input(
            request_type=request_type,
            candidates=(make_metadata("system.snapshot"),),
        )
    )

    assert decision.outcome is DecisionOutcome.REQUEST_PLANNING
    assert decision.target is None


def test_question_delegates_only_to_explicit_allowed_service() -> None:
    decision = make_engine().decide(
        make_input(
            request_type=RequestType.QUESTION,
            allow_delegation=True,
            delegation_service_id="ai.default",
        )
    )

    assert decision.outcome is DecisionOutcome.DELEGATE
    assert decision.target == "ai.default"


@pytest.mark.parametrize(
    "content",
    (
        "abre a calculadora pra mim",
        "quero fazer umas contas",
        "pode abrir o bloco de notas para eu escrever",
        "could you open the calculator?",
        "I want to do some calculations",
        "please open notepad",
    ),
)
def test_eligible_natural_language_request_delegates_to_interpreter(
    content: str,
) -> None:
    decision = make_engine().decide(
        make_input(
            content=content,
            request_type=RequestType.INTENTION,
            confidence=0.25,
            candidates=(
                make_metadata(
                    "application.open",
                    permissions=("application.control",),
                ),
            ),
            permission_grants=("application.control",),
            allow_delegation=True,
            delegation_service_id=REQUEST_INTERPRETER_SERVICE_ID,
        )
    )

    assert decision.outcome is DecisionOutcome.DELEGATE
    assert decision.target == REQUEST_INTERPRETER_SERVICE_ID


@pytest.mark.parametrize(
    "content",
    (
        "open calculator && shutdown",
        "open notepad && calc",
        "open spotify && anything",
        "open calculator | powershell",
        "open calculator $(whoami)",
        "open calculator > output.txt",
        "open calculator and restart",
        "open calculator then open notepad",
        "open calculator please run shutdown",
        "shutdown computer",
        "arbitrary text",
        "run calculator",
    ),
)
def test_suspicious_request_never_delegates_to_interpreter(content: str) -> None:
    decision = make_engine().decide(
        make_input(
            content=content,
            candidates=(make_metadata("application.open"),),
            allow_delegation=True,
            delegation_service_id=REQUEST_INTERPRETER_SERVICE_ID,
        )
    )

    assert decision.outcome is not DecisionOutcome.DELEGATE


def test_valid_interpretation_requires_confirmation_without_execution() -> None:
    decision_input = make_input(
        content="Please open calculator for me",
        request_type=RequestType.INTENTION,
        candidates=(
            make_metadata(
                "application.open",
                permissions=("application.control",),
            ),
        ),
        permission_grants=("application.control",),
        allow_delegation=True,
        delegation_service_id=REQUEST_INTERPRETER_SERVICE_ID,
    )
    interpretation = RequestInterpretation(
        decision_input.request.request_id,
        AIIntent.OPEN_APPLICATION,
        "application.open",
        "calculator",
        0.9,
    )

    decision = make_engine().decide(
        DecisionInput(
            request=decision_input.request,
            classification=decision_input.classification,
            context=decision_input.context,
            memory=decision_input.memory,
            platform_state=decision_input.platform_state,
            user_policy=decision_input.user_policy,
            candidate_capabilities=decision_input.candidate_capabilities,
            interpretation=interpretation,
        )
    )

    assert decision.outcome is DecisionOutcome.ASK_FOR_CONFIRMATION
    assert decision.target == "application.open"
    assert decision.reason_code == "ai_interpretation_requires_confirmation"


def test_interpretation_cannot_select_unavailable_capability() -> None:
    decision_input = make_input(content="Please open calculator for me")
    interpretation = RequestInterpretation(
        decision_input.request.request_id,
        AIIntent.OPEN_APPLICATION,
        "application.open",
        "calculator",
        0.9,
    )

    decision = make_engine().decide(
        DecisionInput(
            request=decision_input.request,
            classification=decision_input.classification,
            context=decision_input.context,
            memory=decision_input.memory,
            platform_state=decision_input.platform_state,
            user_policy=decision_input.user_policy,
            candidate_capabilities=(),
            interpretation=interpretation,
        )
    )

    assert decision.outcome is DecisionOutcome.IGNORE
    assert decision.reason_code == "interpreted_target_unavailable"


def test_interpretation_cannot_bypass_permission_policy() -> None:
    decision_input = make_input(
        content="Please open calculator for me",
        candidates=(
            make_metadata(
                "application.open",
                permissions=("application.control",),
            ),
        ),
    )
    interpretation = RequestInterpretation(
        decision_input.request.request_id,
        AIIntent.OPEN_APPLICATION,
        "application.open",
        "calculator",
        0.9,
    )

    decision = make_engine().decide(
        DecisionInput(
            request=decision_input.request,
            classification=decision_input.classification,
            context=decision_input.context,
            memory=decision_input.memory,
            platform_state=decision_input.platform_state,
            user_policy=decision_input.user_policy,
            candidate_capabilities=decision_input.candidate_capabilities,
            interpretation=interpretation,
        )
    )

    assert decision.outcome is DecisionOutcome.IGNORE
    assert decision.reason_code == "required_permission_missing"


def test_disabled_interruption_returns_suggestion_without_execution() -> None:
    decision = make_engine().decide(
        make_input(
            candidates=(make_metadata("system.snapshot"),),
            allow_interruption=False,
        )
    )

    assert decision.outcome is DecisionOutcome.SUGGEST
    assert decision.reason_code == "interruption_disabled_by_user_policy"
    assert decision.target == "system.snapshot"


def test_no_available_capability_is_ignored() -> None:
    decision = make_engine().decide(make_input())

    assert decision.outcome is DecisionOutcome.IGNORE
    assert decision.reason_code == "no_available_capability"


def test_missing_permissions_never_produces_execute() -> None:
    capability = make_metadata(
        "system.snapshot",
        permissions=("system.metrics.read",),
    )

    decision = make_engine().decide(make_input(candidates=(capability,)))

    assert decision.outcome is DecisionOutcome.IGNORE
    assert decision.reason_code == "required_permission_missing"


def test_missing_permissions_precede_confidence_and_state_restrictions() -> None:
    capability = make_metadata(
        "system.snapshot",
        permissions=("system.metrics.read",),
    )

    decision = make_engine().decide(
        make_input(
            confidence=0.25,
            candidates=(capability,),
            operational_state=OperationalState.STANDBY,
        )
    )

    assert decision.outcome is DecisionOutcome.IGNORE
    assert decision.reason_code == "required_permission_missing"


def test_standby_prevents_execution() -> None:
    decision = make_engine().decide(
        make_input(
            candidates=(make_metadata("system.snapshot"),),
            operational_state=OperationalState.STANDBY,
        )
    )

    assert decision.outcome is DecisionOutcome.IGNORE
    assert decision.reason_code == "operational_state_standby"


def test_inconsistent_request_identity_raises_explicit_error() -> None:
    decision_input = make_input()
    inconsistent = DecisionInput(
        request=decision_input.request,
        classification=ClassifiedRequest(uuid4(), RequestType.COMMAND, 0.9),
        context=decision_input.context,
        memory=decision_input.memory,
        platform_state=decision_input.platform_state,
        user_policy=decision_input.user_policy,
        candidate_capabilities=decision_input.candidate_capabilities,
    )

    with pytest.raises(InconsistentDecisionInputError):
        make_engine().decide(inconsistent)


def test_decision_is_immutable_and_deterministic() -> None:
    decision_input = make_input(candidates=(make_metadata("system.snapshot"),))
    engine = make_engine()

    first = engine.decide(decision_input)
    second = engine.decide(decision_input)

    assert first == second
    with pytest.raises(FrozenInstanceError):
        first.target = "changed"  # type: ignore[misc]
    assert not hasattr(first, "execute")


def test_decision_event_excludes_raw_request_content() -> None:
    event_bus = InProcessEventBus()
    events: list[DecisionMade] = []
    event_bus.subscribe(DecisionMade, events.append)

    make_engine(event_bus).decide(
        make_input(candidates=(make_metadata("system.snapshot"),))
    )

    assert len(events) == 1
    assert not hasattr(events[0], "request")
    assert not hasattr(events[0], "content")


def test_platform_behavior_preserves_independent_current_values() -> None:
    event_bus = InProcessEventBus()
    events: list[PlatformBehaviorDecisionMade] = []
    event_bus.subscribe(PlatformBehaviorDecisionMade, events.append)
    request_input = make_input(
        operational_state=OperationalState.PASSIVE,
        performance_profile=PerformanceProfile.IDLE,
    )
    platform_input = PlatformBehaviorDecisionInput(
        evaluation_id=uuid4(),
        platform_state=request_input.platform_state,
        context=request_input.context,
        system_signals=(),
        configuration_policy=PlatformBehaviorPolicy(
            tuple(OperationalState),
            tuple(PerformanceProfile),
        ),
        user_policy=request_input.user_policy,
        trigger="periodic_evaluation",
    )

    decision = make_engine(event_bus).decide_platform_behavior(platform_input)

    assert decision.desired_operational_state is OperationalState.PASSIVE
    assert decision.desired_performance_profile is PerformanceProfile.IDLE
    assert len(events) == 1
    assert not hasattr(events[0], "applied")


@pytest.mark.parametrize("operational_state", tuple(OperationalState))
@pytest.mark.parametrize("performance_profile", tuple(PerformanceProfile))
def test_platform_behavior_keeps_state_and_profile_independent(
    operational_state: OperationalState,
    performance_profile: PerformanceProfile,
) -> None:
    request_input = make_input(
        operational_state=operational_state,
        performance_profile=performance_profile,
    )
    platform_input = PlatformBehaviorDecisionInput(
        evaluation_id=uuid4(),
        platform_state=request_input.platform_state,
        context=request_input.context,
        system_signals=(),
        configuration_policy=PlatformBehaviorPolicy(
            tuple(OperationalState),
            tuple(PerformanceProfile),
        ),
        user_policy=request_input.user_policy,
        trigger="periodic_evaluation",
    )

    decision = make_engine().decide_platform_behavior(platform_input)

    assert decision.desired_operational_state is operational_state
    assert decision.desired_performance_profile is performance_profile


def test_performance_profile_can_limit_non_command_work() -> None:
    decision = make_engine().decide(
        make_input(
            request_type=RequestType.TASK,
            candidates=(make_metadata("system.snapshot"),),
            performance_profile=PerformanceProfile.PERFORMANCE,
        )
    )

    assert decision.outcome is DecisionOutcome.SUGGEST
    assert decision.reason_code == "performance_profile_limits_non_command_work"


def test_accepted_confirmation_returns_planning_after_current_revalidation() -> None:
    capability = make_metadata(
        "application.open",
        permissions=("application.control",),
    )

    decision = make_engine().decide(
        make_input(
            content="sim",
            candidates=(capability,),
            permission_grants=("application.control",),
            confirmation_status=ConfirmationResolutionStatus.ACCEPTED,
        )
    )

    assert decision.outcome is DecisionOutcome.REQUEST_PLANNING
    assert decision.target == "application.open"
    assert decision.reason_code == "confirmed_action_requires_explicit_plan"


@pytest.mark.parametrize(
    ("status", "reason_code"),
    (
        (ConfirmationResolutionStatus.NO_PENDING, "confirmation_not_pending"),
        (
            ConfirmationResolutionStatus.REJECTED,
            "confirmation_rejected_by_user",
        ),
        (ConfirmationResolutionStatus.INVALIDATED, "confirmation_invalidated"),
        (ConfirmationResolutionStatus.EXPIRED, "confirmation_expired"),
    ),
)
def test_non_accepted_confirmation_statuses_return_safe_ignore(
    status: ConfirmationResolutionStatus,
    reason_code: str,
) -> None:
    decision = make_engine().decide(
        make_input(content="sim", confirmation_status=status)
    )

    assert decision.outcome is DecisionOutcome.IGNORE
    assert decision.reason_code == reason_code


@pytest.mark.parametrize(
    ("available", "permission_grants", "operational_state", "reason_code"),
    (
        (
            False,
            ("application.control",),
            OperationalState.ACTIVE,
            "confirmed_target_unavailable",
        ),
        (True, (), OperationalState.ACTIVE, "required_permission_missing"),
        (
            True,
            ("application.control",),
            OperationalState.STANDBY,
            "operational_state_standby",
        ),
    ),
)
def test_accepted_confirmation_does_not_freeze_current_execution_preconditions(
    available: bool,
    permission_grants: tuple[str, ...],
    operational_state: OperationalState,
    reason_code: str,
) -> None:
    capability = make_metadata(
        "application.open",
        permissions=("application.control",),
        available=available,
    )

    decision = make_engine().decide(
        make_input(
            content="yes",
            candidates=(capability,),
            permission_grants=permission_grants,
            operational_state=operational_state,
            confirmation_status=ConfirmationResolutionStatus.ACCEPTED,
        )
    )

    assert decision.outcome is DecisionOutcome.IGNORE
    assert decision.reason_code == reason_code


def test_not_applicable_resolution_cannot_enter_confirmation_decision() -> None:
    with pytest.raises(InconsistentDecisionInputError):
        make_engine().decide(
            make_input(
                confirmation_status=ConfirmationResolutionStatus.NOT_APPLICABLE
            )
        )


def test_accepted_confirmation_requires_response_request_correlation() -> None:
    decision_input = make_input(
        confirmation_status=ConfirmationResolutionStatus.ACCEPTED
    )
    assert decision_input.confirmation is not None
    invalid_resolution = replace(
        decision_input.confirmation,
        response_request_id=uuid4(),
    )

    with pytest.raises(InconsistentDecisionInputError):
        make_engine().decide(
            replace(decision_input, confirmation=invalid_resolution)
        )


def test_accepted_confirmation_rejects_original_request_replay() -> None:
    decision_input = make_input(
        confirmation_status=ConfirmationResolutionStatus.ACCEPTED
    )
    assert decision_input.confirmation is not None
    assert decision_input.confirmation.pending is not None
    replayed_pending = replace(
        decision_input.confirmation.pending,
        original_request_id=decision_input.request.request_id,
    )
    invalid_resolution = replace(
        decision_input.confirmation,
        pending=replayed_pending,
    )

    with pytest.raises(InconsistentDecisionInputError):
        make_engine().decide(
            replace(decision_input, confirmation=invalid_resolution)
        )


def test_accepted_confirmation_rejects_expired_resolution() -> None:
    decision_input = make_input(
        confirmation_status=ConfirmationResolutionStatus.ACCEPTED
    )
    assert decision_input.confirmation is not None
    assert decision_input.confirmation.pending is not None
    invalid_resolution = replace(
        decision_input.confirmation,
        resolved_at=decision_input.confirmation.pending.expires_at,
    )

    with pytest.raises(InconsistentDecisionInputError):
        make_engine().decide(
            replace(decision_input, confirmation=invalid_resolution)
        )
