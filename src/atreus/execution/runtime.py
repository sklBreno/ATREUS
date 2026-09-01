"""Synchronous in-process Capability Runtime implementation."""

from datetime import datetime

from atreus.ai.models import AIProviderAvailabilityState
from atreus.capability.contracts import CapabilityArgument, CapabilityOutputItem
from atreus.capability.models import CapabilityAvailabilityState
from atreus.context.models import ContextSnapshot
from atreus.execution.exceptions import (
    CapabilityAIUnavailableError,
    DuplicateCapabilityImplementationError,
    InvalidCapabilityInvocationError,
    InvalidCapabilityLoadingError,
    MissingCapabilityPermissionsError,
    UnavailableRuntimeCapabilityError,
    UnknownRuntimeCapabilityError,
    UnsupportedExecutionDeadlineError,
)
from atreus.execution.models import (
    CapabilityExecutionCompleted,
    CapabilityExecutionFailed,
    CapabilityExecutionResult,
    CapabilityExecutionStarted,
    CapabilityExecutionStatus,
    CapabilityInvocation,
    ExecutionContext,
)
from atreus.interfaces.ai_availability import AIAvailabilityProvider
from atreus.interfaces.cancellation import CancellationSignal
from atreus.interfaces.capability import Capability
from atreus.interfaces.capability_registry import CapabilityRegistry
from atreus.interfaces.capability_runtime import CapabilityRuntime
from atreus.interfaces.clock import Clock
from atreus.interfaces.event_bus import EventBus


class InProcessCapabilityRuntime(CapabilityRuntime):
    """Load and invoke trusted capabilities through explicit dependencies."""

    def __init__(
        self,
        registry: CapabilityRegistry,
        ai_availability_provider: AIAvailabilityProvider,
        cancellation: CancellationSignal,
        clock: Clock,
        event_bus: EventBus | None = None,
    ) -> None:
        """Initialize the runtime with all external state boundaries.

        Args:
            registry: Authoritative metadata registration and lookup boundary.
            ai_availability_provider: Current AI availability source.
            cancellation: Cooperative cancellation signal for invocations.
            clock: Time source for terminal result metadata.
            event_bus: Event Bus used for execution lifecycle events.
        """
        self._registry = registry
        self._ai_availability_provider = ai_availability_provider
        self._cancellation = cancellation
        self._clock = clock
        self._event_bus = event_bus
        self._implementations: dict[str, Capability] = {}
        self._load_completed = False

    def load(self, capabilities: tuple[Capability, ...]) -> None:
        """Load explicit implementations, register metadata, and seal catalog.

        Args:
            capabilities: Trusted local capability implementations.

        Raises:
            InvalidCapabilityLoadingError: If loading was completed or invalid.
            DuplicateCapabilityImplementationError: If identifiers repeat.
        """
        if self._load_completed:
            raise InvalidCapabilityLoadingError(
                "Capability Runtime loading has already completed."
            )
        if not isinstance(capabilities, tuple) or any(
            not isinstance(capability, Capability) for capability in capabilities
        ):
            raise InvalidCapabilityLoadingError(
                "Runtime loading requires a tuple of Capability implementations."
            )
        identifiers = tuple(
            capability.metadata.identifier for capability in capabilities
        )
        if len(identifiers) != len(set(identifiers)):
            raise DuplicateCapabilityImplementationError(
                "Capability implementation identifiers must be unique."
            )
        for identifier in identifiers:
            if self._registry.get(identifier) is not None:
                raise DuplicateCapabilityImplementationError(
                    f"Capability '{identifier}' is already registered."
                )

        for capability in capabilities:
            self._registry.register(capability.metadata)
            self._implementations[capability.metadata.identifier] = capability
        self._registry.seal()
        self._load_completed = True

    def invoke(
        self,
        invocation: CapabilityInvocation,
    ) -> CapabilityExecutionResult:
        """Validate and invoke one capability with terminal failure isolation.

        Args:
            invocation: Immutable capability invocation request.

        Returns:
            Exactly one immutable terminal execution result after start.

        Raises:
            InvalidCapabilityInvocationError: If invocation structure is invalid.
            UnknownRuntimeCapabilityError: If metadata or implementation is absent.
            UnavailableRuntimeCapabilityError: If availability prevents execution.
            MissingCapabilityPermissionsError: If grants are incomplete.
            CapabilityAIUnavailableError: If required AI is not available.
            UnsupportedExecutionDeadlineError: If a deadline is requested.
        """
        self._validate_invocation(invocation)
        metadata = self._registry.get(invocation.capability_id)
        if metadata is None:
            raise UnknownRuntimeCapabilityError(
                f"Capability '{invocation.capability_id}' is not registered."
            )
        capability = self._implementations.get(invocation.capability_id)
        if capability is None:
            raise UnknownRuntimeCapabilityError(
                f"Capability '{invocation.capability_id}' is not loaded."
            )
        if metadata.availability.state is not CapabilityAvailabilityState.AVAILABLE:
            raise UnavailableRuntimeCapabilityError(
                f"Capability '{invocation.capability_id}' is not available."
            )
        self._validate_dependencies(metadata.dependencies)
        if not set(metadata.permissions).issubset(invocation.permission_grants):
            raise MissingCapabilityPermissionsError(
                f"Capability '{invocation.capability_id}' lacks required grants."
            )
        if (
            metadata.requires_ai
            and self._ai_availability_provider.availability().state
            is not AIProviderAvailabilityState.AVAILABLE
        ):
            raise CapabilityAIUnavailableError(
                f"Capability '{invocation.capability_id}' requires available AI."
            )

        started_at = self._clock.now()
        self._publish_started(invocation)
        try:
            cancelled = self._cancellation.is_cancelled()
        except Exception:
            return self._failed_result(
                invocation,
                started_at,
                CapabilityExecutionStatus.FAILED,
                "capability_execution_failed",
                completed_at=started_at,
            )
        if cancelled:
            return self._failed_result(
                invocation,
                started_at,
                CapabilityExecutionStatus.CANCELLED,
                "capability_execution_cancelled",
                completed_at=started_at,
            )

        try:
            context = ExecutionContext(
                invocation_id=invocation.invocation_id,
                request_id=invocation.request_id,
                plan_id=invocation.plan_id,
                step_id=invocation.step_id,
                context=invocation.context,
                permission_grants=invocation.permission_grants,
                cancellation=self._cancellation,
            )
            output = capability.execute(invocation.arguments, context)
            if not isinstance(output, tuple) or any(
                not isinstance(item, CapabilityOutputItem) for item in output
            ):
                raise TypeError("Capability output contract is invalid.")
            completed_at = self._clock.now()
        except Exception:
            return self._failed_result(
                invocation,
                started_at,
                CapabilityExecutionStatus.FAILED,
                "capability_execution_failed",
                completed_at=started_at,
            )

        duration_seconds = (completed_at - started_at).total_seconds()
        result = CapabilityExecutionResult(
            invocation_id=invocation.invocation_id,
            capability_id=invocation.capability_id,
            status=CapabilityExecutionStatus.SUCCEEDED,
            output=output,
            error_code=None,
            started_at=started_at,
            completed_at=completed_at,
        )
        self._publish_completed(invocation, duration_seconds)
        return result

    def _validate_invocation(self, invocation: CapabilityInvocation) -> None:
        if not self._load_completed:
            raise InvalidCapabilityInvocationError(
                "Capability Runtime loading must complete before invocation."
            )
        if not isinstance(invocation, CapabilityInvocation):
            raise InvalidCapabilityInvocationError(
                "Runtime invocation requires CapabilityInvocation."
            )
        if not invocation.capability_id.strip():
            raise InvalidCapabilityInvocationError(
                "Invocation capability identifier must be non-empty."
            )
        if not isinstance(invocation.context, ContextSnapshot):
            raise InvalidCapabilityInvocationError(
                "Invocation context must be a ContextSnapshot."
            )
        if not isinstance(invocation.arguments, tuple) or any(
            not isinstance(argument, CapabilityArgument)
            for argument in invocation.arguments
        ):
            raise InvalidCapabilityInvocationError(
                "Invocation arguments must be immutable CapabilityArgument values."
            )
        argument_names = tuple(
            argument.name for argument in invocation.arguments
        )
        if len(argument_names) != len(set(argument_names)) or any(
            not name.strip() for name in argument_names
        ):
            raise InvalidCapabilityInvocationError(
                "Invocation argument names must be non-empty and unique."
            )
        if (
            invocation.timeout_seconds is not None
            and invocation.timeout_seconds <= 0
        ):
            raise InvalidCapabilityInvocationError(
                "Invocation timeout must be positive when provided."
            )
        if invocation.timeout_seconds is not None:
            raise UnsupportedExecutionDeadlineError(
                "The synchronous Runtime cannot enforce execution deadlines."
            )
        if len(invocation.permission_grants) != len(
            set(invocation.permission_grants)
        ):
            raise InvalidCapabilityInvocationError(
                "Invocation permission grants must be unique."
            )

    def _validate_dependencies(self, dependencies: tuple[str, ...]) -> None:
        for dependency in dependencies:
            metadata = self._registry.get(dependency)
            if metadata is None or (
                metadata.availability.state
                is not CapabilityAvailabilityState.AVAILABLE
            ):
                raise UnavailableRuntimeCapabilityError(
                    f"Capability dependency '{dependency}' is unavailable."
                )

    def _failed_result(
        self,
        invocation: CapabilityInvocation,
        started_at: datetime,
        status: CapabilityExecutionStatus,
        error_code: str,
        *,
        completed_at: datetime | None = None,
    ) -> CapabilityExecutionResult:
        terminal_at = completed_at if completed_at is not None else self._clock.now()
        result = CapabilityExecutionResult(
            invocation_id=invocation.invocation_id,
            capability_id=invocation.capability_id,
            status=status,
            output=None,
            error_code=error_code,
            started_at=started_at,
            completed_at=terminal_at,
        )
        self._publish_failed(invocation, status, error_code)
        return result

    def _publish_started(self, invocation: CapabilityInvocation) -> None:
        if self._event_bus is None:
            return
        self._event_bus.publish(
            CapabilityExecutionStarted(
                source="capability_runtime",
                correlation_id=invocation.request_id,
                invocation_id=invocation.invocation_id,
                request_id=invocation.request_id,
                capability_id=invocation.capability_id,
                plan_id=invocation.plan_id,
                step_id=invocation.step_id,
            )
        )

    def _publish_completed(
        self,
        invocation: CapabilityInvocation,
        duration_seconds: float,
    ) -> None:
        if self._event_bus is None:
            return
        self._event_bus.publish(
            CapabilityExecutionCompleted(
                source="capability_runtime",
                correlation_id=invocation.request_id,
                invocation_id=invocation.invocation_id,
                request_id=invocation.request_id,
                capability_id=invocation.capability_id,
                plan_id=invocation.plan_id,
                step_id=invocation.step_id,
                duration_seconds=duration_seconds,
            )
        )

    def _publish_failed(
        self,
        invocation: CapabilityInvocation,
        status: CapabilityExecutionStatus,
        error_code: str,
    ) -> None:
        if self._event_bus is None:
            return
        self._event_bus.publish(
            CapabilityExecutionFailed(
                source="capability_runtime",
                correlation_id=invocation.request_id,
                invocation_id=invocation.invocation_id,
                request_id=invocation.request_id,
                capability_id=invocation.capability_id,
                plan_id=invocation.plan_id,
                step_id=invocation.step_id,
                terminal_status=status,
                error_code=error_code,
            )
        )
