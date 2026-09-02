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
from atreus.interfaces.application_launcher import ApplicationLauncher
from atreus.interfaces.application_state_reader import ApplicationStateReader
from atreus.interfaces.capability import Capability
from atreus.interfaces.clock import Clock
from atreus.interfaces.context import ContextProvider
from atreus.interfaces.log_writer import LogWriter
from atreus.interfaces.memory import MemorySnapshotProvider
from atreus.logging.models import StructuredLogRecord
from atreus.memory.models import MemorySnapshot
from atreus.system.models import (
    ApplicationInstance,
    ApplicationLaunchRequest,
    ApplicationState,
    ApplicationStatusRequest,
    ApplicationStatusResult,
    SystemOperationContext,
)

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
        self.call_count = 0

    def current_context(self) -> ContextSnapshot:
        """Return the configured snapshot."""
        self.call_count += 1
        return self._snapshot


class StaticMemorySnapshotProvider(MemorySnapshotProvider):
    """Return one immutable Working Memory snapshot."""

    def __init__(self, snapshot: MemorySnapshot | None = None) -> None:
        """Initialize the provider with an empty or explicit snapshot."""
        self._snapshot = snapshot or MemorySnapshot(NOW, ())
        self.call_count = 0

    def snapshot(self) -> MemorySnapshot:
        """Return the configured snapshot while recording the read."""
        self.call_count += 1
        return self._snapshot


class StaticAIAvailabilityProvider(AIAvailabilityProvider):
    """Return one immutable AI availability value."""

    def __init__(self, availability: AIProviderAvailability) -> None:
        """Initialize the current AI availability."""
        self._availability = availability

    def availability(self) -> AIProviderAvailability:
        """Return the configured availability."""
        return self._availability


class RecordingApplicationLauncher(ApplicationLauncher):
    """Record approved application launches without native side effects."""

    def __init__(self, process_id: int = 4242) -> None:
        """Initialize the controller with a deterministic process identifier."""
        self._process_id = process_id
        self.calls: list[tuple[ApplicationLaunchRequest, SystemOperationContext]] = []

    def launch(
        self,
        request: ApplicationLaunchRequest,
        context: SystemOperationContext,
    ) -> ApplicationInstance:
        """Record and return one normalized application instance."""
        self.calls.append((request, context))
        return ApplicationInstance(request.application_id, self._process_id)


class RecordingApplicationStateReader(ApplicationStateReader):
    """Record approved state reads without native process inspection."""

    def __init__(self, state: ApplicationState = ApplicationState.NOT_RUNNING) -> None:
        """Initialize the reader with one deterministic state."""
        self._state = state
        self.calls: list[tuple[ApplicationStatusRequest, SystemOperationContext]] = []

    def read_status(
        self,
        request: ApplicationStatusRequest,
        context: SystemOperationContext,
    ) -> ApplicationStatusResult:
        """Record and return one normalized application state."""
        self.calls.append((request, context))
        return ApplicationStatusResult(request.application_id, self._state)


class RecordingLogWriter(LogWriter):
    """Retain structured records without filesystem access."""

    def __init__(self) -> None:
        """Initialize an empty record collection."""
        self.records: list[StructuredLogRecord] = []

    def write(self, record: StructuredLogRecord) -> None:
        """Record one structured observability value.

        Args:
            record: Sanitized record produced by the observer.
        """
        self.records.append(record)


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
