"""Shared deterministic test doubles for ATREUS runtime tests."""

from datetime import UTC, datetime

from atreus.ai.models import AIProviderAvailability
from atreus.capability.contracts import (
    CapabilityArguments,
    CapabilityOutput,
    CapabilityOutputItem,
)
from atreus.capability.models import CapabilityMetadata
from atreus.context.models import ContextSnapshot
from atreus.execution.models import ExecutionContext
from atreus.interfaces.ai_availability import AIAvailabilityProvider
from atreus.interfaces.capability import Capability
from atreus.interfaces.clock import Clock
from atreus.interfaces.context import ContextProvider

NOW = datetime(2026, 8, 31, 12, 0, tzinfo=UTC)


class FixedClock(Clock):
    """Return one fixed timestamp for deterministic tests."""

    def __init__(self, timestamp: datetime = NOW) -> None:
        """Initialize the fixed timestamp."""
        self._timestamp = timestamp

    def now(self) -> datetime:
        """Return the configured timestamp."""
        return self._timestamp


class StaticContextProvider(ContextProvider):
    """Return one immutable context snapshot."""

    def __init__(self, snapshot: ContextSnapshot) -> None:
        """Initialize the current context snapshot."""
        self._snapshot = snapshot

    def current_context(self) -> ContextSnapshot:
        """Return the configured snapshot."""
        return self._snapshot


class StaticAIAvailabilityProvider(AIAvailabilityProvider):
    """Return one immutable AI availability value."""

    def __init__(self, availability: AIProviderAvailability) -> None:
        """Initialize the current AI availability."""
        self._availability = availability

    def availability(self) -> AIProviderAvailability:
        """Return the configured availability."""
        return self._availability


class RecordingCapability(Capability):
    """Record invocations and optionally raise a test failure."""

    def __init__(
        self,
        metadata: CapabilityMetadata,
        *,
        output: CapabilityOutput = (),
        error: Exception | None = None,
    ) -> None:
        """Initialize capability behavior for a test."""
        self._metadata = metadata
        self._output = output
        self._error = error
        self.calls: list[tuple[CapabilityArguments, ExecutionContext]] = []

    @property
    def metadata(self) -> CapabilityMetadata:
        """Return immutable test metadata."""
        return self._metadata

    def execute(
        self,
        arguments: CapabilityArguments,
        context: ExecutionContext,
    ) -> CapabilityOutput:
        """Record the invocation and return or raise configured behavior."""
        self.calls.append((arguments, context))
        if self._error is not None:
            raise self._error
        return self._output


SUCCESS_OUTPUT = (CapabilityOutputItem("status", "ok"),)
