"""Executable capability contract used by Capability Runtime."""

from abc import ABC, abstractmethod

from atreus.capability.contracts import CapabilityArguments, CapabilityOutput
from atreus.capability.models import CapabilityMetadata
from atreus.execution.models import ExecutionContext


class Capability(ABC):
    """Define one explicitly loaded executable capability boundary."""

    @property
    @abstractmethod
    def metadata(self) -> CapabilityMetadata:
        """Return immutable metadata matching the implementation identity."""

    @abstractmethod
    def execute(
        self,
        arguments: CapabilityArguments,
        context: ExecutionContext,
    ) -> CapabilityOutput:
        """Execute one validated capability invocation.

        Args:
            arguments: Immutable named capability inputs.
            context: Correlation, context, grants, and cancellation metadata.

        Returns:
            Immutable named capability output values.
        """
