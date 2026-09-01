"""Capability Runtime contract exposed to Core orchestration."""

from abc import ABC, abstractmethod

from atreus.execution.models import (
    CapabilityExecutionResult,
    CapabilityInvocation,
)
from atreus.interfaces.capability import Capability


class CapabilityRuntime(ABC):
    """Define explicit loading and one-at-a-time capability invocation."""

    @abstractmethod
    def load(self, capabilities: tuple[Capability, ...]) -> None:
        """Load trusted local implementations and seal registration.

        Args:
            capabilities: Explicit immutable collection of implementations.
        """

    @abstractmethod
    def invoke(
        self,
        invocation: CapabilityInvocation,
    ) -> CapabilityExecutionResult:
        """Invoke one capability through the controlled runtime boundary.

        Args:
            invocation: Validated immutable invocation request.

        Returns:
            One immutable terminal execution result.
        """
