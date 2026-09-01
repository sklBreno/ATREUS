"""Deterministic Version 1 Decision Engine implementation."""

from uuid import UUID

from atreus.capability.models import (
    CapabilityAvailabilityState,
    CapabilityMetadata,
)
from atreus.decision.exceptions import InconsistentDecisionInputError
from atreus.decision.models import (
    Decision,
    DecisionInput,
    DecisionMade,
    DecisionOutcome,
    DecisionPolicy,
    PlatformBehaviorDecision,
    PlatformBehaviorDecisionInput,
    PlatformBehaviorDecisionMade,
)
from atreus.interfaces.decision_engine import DecisionEngine
from atreus.interfaces.event_bus import EventBus
from atreus.request_classifier.models import RequestType
from atreus.shared.platform import OperationalState, PerformanceProfile


class DeterministicDecisionEngine(DecisionEngine):
    """Apply bounded local policy without routing or executing work."""

    def __init__(
        self,
        policy: DecisionPolicy,
        event_bus: EventBus | None = None,
    ) -> None:
        """Initialize deterministic policy and optional event publication.

        Args:
            policy: Injected thresholds governing deterministic decisions.
            event_bus: Event Bus used to publish successful decisions.

        Raises:
            InconsistentDecisionInputError: If policy values are invalid.
        """
        if not isinstance(policy, DecisionPolicy) or not (
            0.0 <= policy.minimum_confidence <= 1.0
        ):
            raise InconsistentDecisionInputError(
                "Decision policy confidence must be between 0.0 and 1.0."
            )
        self._policy = policy
        self._event_bus = event_bus

    def decide(self, decision_input: DecisionInput) -> Decision:
        """Select one explicit outcome without performing orchestration.

        Args:
            decision_input: Coherent immutable request decision inputs.

        Returns:
            The immutable decision selected by deterministic policy.

        Raises:
            InconsistentDecisionInputError: If inputs are invalid or unrelated.
        """
        self._validate_decision_input(decision_input)
        decision = self._evaluate_request(decision_input)
        self._publish_decision(decision)
        return decision

    def decide_platform_behavior(
        self,
        decision_input: PlatformBehaviorDecisionInput,
    ) -> PlatformBehaviorDecision:
        """Preserve current state and profile under conservative Phase B policy.

        Args:
            decision_input: Coherent immutable platform evaluation inputs.

        Returns:
            Current independent values as the desired safe behavior.

        Raises:
            InconsistentDecisionInputError: If inputs or policy are invalid.
        """
        self._validate_platform_behavior_input(decision_input)
        decision = PlatformBehaviorDecision(
            evaluation_id=decision_input.evaluation_id,
            desired_operational_state=(
                decision_input.platform_state.operational_state
            ),
            operational_state_reason_code="current_operational_state_preserved",
            desired_performance_profile=(
                decision_input.platform_state.performance_profile
            ),
            performance_profile_reason_code="current_performance_profile_preserved",
        )
        self._publish_platform_behavior_decision(decision)
        return decision

    def _evaluate_request(self, decision_input: DecisionInput) -> Decision:
        request_id = decision_input.request.request_id
        candidates = tuple(
            metadata
            for metadata in decision_input.candidate_capabilities
            if metadata.availability.state
            is CapabilityAvailabilityState.AVAILABLE
        )
        explicitly_targeted = self._explicitly_targeted_capabilities(
            decision_input.request.content,
            candidates,
        )
        unblocked = tuple(
            metadata
            for metadata in explicitly_targeted
            if metadata.identifier
            not in decision_input.user_policy.blocked_capability_ids
        )
        permitted = tuple(
            metadata
            for metadata in unblocked
            if set(metadata.permissions).issubset(
                decision_input.user_policy.permission_grants
            )
        )

        request_type = decision_input.classification.request_type
        capability_request = request_type in (
            RequestType.COMMAND,
            RequestType.INTENTION,
            RequestType.TASK,
        )
        if candidates and capability_request and not explicitly_targeted:
            return Decision(
                request_id,
                DecisionOutcome.ASK_FOR_CONFIRMATION,
                None,
                "capability_target_not_established",
            )
        if explicitly_targeted and not unblocked:
            return Decision(
                request_id,
                DecisionOutcome.IGNORE,
                None,
                "capability_blocked_by_user_policy",
            )
        if unblocked and not permitted:
            return Decision(
                request_id,
                DecisionOutcome.IGNORE,
                None,
                "required_permission_missing",
            )
        if (
            decision_input.platform_state.operational_state
            is OperationalState.STANDBY
        ):
            return Decision(
                request_id,
                DecisionOutcome.IGNORE,
                None,
                "operational_state_standby",
            )
        if (
            decision_input.classification.confidence
            < self._policy.minimum_confidence
        ):
            return Decision(
                request_id,
                DecisionOutcome.ASK_FOR_CONFIRMATION,
                None,
                "classification_confidence_below_policy",
            )
        if not decision_input.user_policy.allow_interruption:
            return Decision(
                request_id,
                DecisionOutcome.SUGGEST,
                self._single_target(permitted),
                "interruption_disabled_by_user_policy",
            )
        if (
            decision_input.platform_state.performance_profile
            is PerformanceProfile.PERFORMANCE
            and decision_input.classification.request_type
            is not RequestType.COMMAND
        ):
            return Decision(
                request_id,
                DecisionOutcome.SUGGEST,
                self._single_target(permitted),
                "performance_profile_limits_non_command_work",
            )

        if request_type is RequestType.COMMAND:
            return self._decide_command(request_id, unblocked, permitted)
        if request_type in (RequestType.INTENTION, RequestType.TASK):
            if permitted:
                return Decision(
                    request_id,
                    DecisionOutcome.REQUEST_PLANNING,
                    None,
                    "request_requires_explicit_plan",
                )
            return self._unavailable_or_denied_decision(
                request_id,
                unblocked,
            )
        if (
            request_type in (RequestType.QUESTION, RequestType.CONVERSATION)
            and decision_input.user_policy.allow_delegation
            and decision_input.user_policy.delegation_service_id
        ):
            return Decision(
                request_id,
                DecisionOutcome.DELEGATE,
                decision_input.user_policy.delegation_service_id,
                "delegation_service_available",
            )
        return Decision(
            request_id,
            DecisionOutcome.SUGGEST,
            self._single_target(permitted),
            "no_execution_route_selected",
        )

    @staticmethod
    def _decide_command(
        request_id: UUID,
        unblocked: tuple[CapabilityMetadata, ...],
        permitted: tuple[CapabilityMetadata, ...],
    ) -> Decision:
        if not permitted:
            return DeterministicDecisionEngine._unavailable_or_denied_decision(
                request_id,
                unblocked,
            )
        if len(permitted) > 1:
            return Decision(
                request_id,
                DecisionOutcome.ASK_FOR_CONFIRMATION,
                None,
                "multiple_capability_targets",
            )
        return Decision(
            request_id,
            DecisionOutcome.EXECUTE,
            permitted[0].identifier,
            "single_eligible_capability",
        )

    @staticmethod
    def _unavailable_or_denied_decision(
        request_id: UUID,
        unblocked: tuple[CapabilityMetadata, ...],
    ) -> Decision:
        reason_code = (
            "required_permission_missing"
            if unblocked
            else "no_available_capability"
        )
        return Decision(
            request_id,
            DecisionOutcome.IGNORE,
            None,
            reason_code,
        )

    @staticmethod
    def _single_target(
        candidates: tuple[CapabilityMetadata, ...],
    ) -> str | None:
        if len(candidates) == 1:
            return candidates[0].identifier
        return None

    @staticmethod
    def _explicitly_targeted_capabilities(
        request_content: str,
        candidates: tuple[CapabilityMetadata, ...],
    ) -> tuple[CapabilityMetadata, ...]:
        content_tokens = request_content.casefold().split()
        return tuple(
            metadata
            for metadata in candidates
            if metadata.identifier.casefold() in content_tokens
        )

    @staticmethod
    def _validate_decision_input(decision_input: DecisionInput) -> None:
        if not isinstance(decision_input, DecisionInput):
            raise InconsistentDecisionInputError(
                "Decision evaluation requires DecisionInput."
            )
        if (
            decision_input.request.request_id
            != decision_input.classification.request_id
        ):
            raise InconsistentDecisionInputError(
                "Request and classification identifiers do not match."
            )
        if not 0.0 <= decision_input.classification.confidence <= 1.0:
            raise InconsistentDecisionInputError(
                "Classification confidence must be between 0.0 and 1.0."
            )
        identifiers = tuple(
            metadata.identifier
            for metadata in decision_input.candidate_capabilities
        )
        if len(identifiers) != len(set(identifiers)):
            raise InconsistentDecisionInputError(
                "Candidate capability identifiers must be unique."
            )

    @staticmethod
    def _validate_platform_behavior_input(
        decision_input: PlatformBehaviorDecisionInput,
    ) -> None:
        if not isinstance(decision_input, PlatformBehaviorDecisionInput):
            raise InconsistentDecisionInputError(
                "Platform evaluation requires PlatformBehaviorDecisionInput."
            )
        if not decision_input.trigger.strip():
            raise InconsistentDecisionInputError(
                "Platform evaluation trigger must be non-empty."
            )
        policy = decision_input.configuration_policy
        if (
            decision_input.platform_state.operational_state
            not in policy.allowed_operational_states
            or decision_input.platform_state.performance_profile
            not in policy.allowed_performance_profiles
        ):
            raise InconsistentDecisionInputError(
                "Current platform behavior is disallowed by configuration policy."
            )

    def _publish_decision(self, decision: Decision) -> None:
        if self._event_bus is None:
            return
        self._event_bus.publish(
            DecisionMade(
                source="decision_engine",
                correlation_id=decision.request_id,
                request_id=decision.request_id,
                outcome=decision.outcome,
                target=decision.target,
                reason_code=decision.reason_code,
            )
        )

    def _publish_platform_behavior_decision(
        self,
        decision: PlatformBehaviorDecision,
    ) -> None:
        if self._event_bus is None:
            return
        self._event_bus.publish(
            PlatformBehaviorDecisionMade(
                source="decision_engine",
                correlation_id=decision.evaluation_id,
                evaluation_id=decision.evaluation_id,
                desired_operational_state=decision.desired_operational_state,
                operational_state_reason_code=(
                    decision.operational_state_reason_code
                ),
                desired_performance_profile=(
                    decision.desired_performance_profile
                ),
                performance_profile_reason_code=(
                    decision.performance_profile_reason_code
                ),
            )
        )
