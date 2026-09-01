"""Decision Engine contracts exposed to Core orchestration."""

from abc import ABC, abstractmethod

from atreus.decision.models import (
    Decision,
    DecisionInput,
    PlatformBehaviorDecision,
    PlatformBehaviorDecisionInput,
)


class DecisionEngine(ABC):
    """Define request and platform behavior decision operations."""

    @abstractmethod
    def decide(self, decision_input: DecisionInput) -> Decision:
        """Select the next orchestration outcome for one request.

        Args:
            decision_input: Coherent immutable request decision inputs.

        Returns:
            The immutable decision selected by policy.
        """

    @abstractmethod
    def decide_platform_behavior(
        self,
        decision_input: PlatformBehaviorDecisionInput,
    ) -> PlatformBehaviorDecision:
        """Select desired operational state and performance profile values.

        Args:
            decision_input: Coherent immutable platform evaluation inputs.

        Returns:
            Desired values for Core to validate and apply.
        """
