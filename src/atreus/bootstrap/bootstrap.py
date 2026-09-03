"""Production dependency composition for the ATREUS local runtime."""

import os
from datetime import timedelta
from pathlib import Path

from atreus.ai.conversation_responder import ProviderBackedConversationResponder
from atreus.ai.models import (
    CONVERSATION_RESPONDER_SERVICE_ID,
    REQUEST_INTERPRETER_SERVICE_ID,
    AIProviderAvailabilityState,
)
from atreus.ai.ollama_provider import OllamaProvider
from atreus.ai.request_interpreter import StructuredRequestInterpreter
from atreus.ai.unavailable_availability import UnavailableAIAvailabilityProvider
from atreus.capability.application_status import ApplicationStatusCapability
from atreus.capability.contracts import (
    APPLICATION_STATUS_CAPABILITY_ID,
    OPEN_APPLICATION_CAPABILITY_ID,
)
from atreus.capability.open_application import OpenApplicationCapability
from atreus.capability.registry import InMemoryCapabilityRegistry
from atreus.configuration.configuration import Configuration
from atreus.configuration.configuration_manager import ConfigurationManager
from atreus.confirmation.coordinator import InMemoryConfirmationCoordinator
from atreus.context.unavailable_context import UnavailableContextProvider
from atreus.conversation.history import InMemoryConversationHistory
from atreus.conversation.models import ConversationHistoryPolicy
from atreus.core.core import Core
from atreus.decision.decision_engine import DeterministicDecisionEngine
from atreus.decision.models import DecisionPolicy, UserPolicy
from atreus.events.event_bus import InProcessEventBus
from atreus.execution.runtime import InProcessCapabilityRuntime
from atreus.interaction.language import DeterministicInteractionLanguageResolver
from atreus.interfaces.ai_provider import AIProvider
from atreus.interfaces.application_launcher import ApplicationLauncher
from atreus.interfaces.application_state_reader import ApplicationStateReader
from atreus.interfaces.clock import Clock
from atreus.interfaces.configuration import ConfigurationProvider
from atreus.interfaces.log_writer import LogWriter
from atreus.logging.event_observer import EventLogObserver
from atreus.logging.jsonl_writer import JsonLinesLogWriter
from atreus.memory.models import WorkingMemoryPolicy
from atreus.memory.working_memory import InMemoryWorkingMemory
from atreus.planner.models import PlanningConstraints
from atreus.planner.planner import DeterministicPlanner
from atreus.request_classifier.classifier import DeterministicRequestClassifier
from atreus.runtime.console import InputReader, InteractiveConsole, OutputWriter
from atreus.runtime.host import RuntimeHost
from atreus.runtime.runtime import InteractiveRuntime
from atreus.shared.cancellation import StaticCancellationSignal
from atreus.shared.clock import UTCClock
from atreus.shared.platform import (
    OperationalState,
    PerformanceProfile,
    PlatformStateSnapshot,
)
from atreus.system.windows_application_launcher import WindowsApplicationLauncher
from atreus.system.windows_application_state_reader import (
    WindowsApplicationStateReader,
)

_INTERACTIVE_V0_MINIMUM_CONFIDENCE = 0.5
_INTERACTIVE_V0_MAXIMUM_PLAN_STEPS = 1
_OBSERVABILITY_V0_LOG_PATH = Path("logs/atreus.log")


class Bootstrap:
    """Compose the concrete dependencies required by the local runtime."""

    def __init__(
        self,
        configuration_provider: ConfigurationProvider | None = None,
        application_launcher: ApplicationLauncher | None = None,
        application_state_reader: ApplicationStateReader | None = None,
        clock: Clock | None = None,
        permission_grants: tuple[str, ...] | None = None,
        log_writer: LogWriter | None = None,
        log_path: Path = _OBSERVABILITY_V0_LOG_PATH,
        ai_provider: AIProvider | None = None,
    ) -> None:
        """Initialize Bootstrap with injectable infrastructure boundaries.

        Args:
            configuration_provider: Provider for the validated application
                configuration.
            application_launcher: Controlled desktop application-launch boundary.
            application_state_reader: Read-only desktop application boundary.
            clock: Time source shared by production runtime components.
            permission_grants: Explicit grants supplied to Runtime enforcement.
            log_writer: Optional injected structured logging boundary.
            log_path: Local JSON Lines destination used by the default writer.
            ai_provider: Optional injected provider used instead of composition.
        """
        self._configuration_provider = (
            configuration_provider
            if configuration_provider is not None
            else ConfigurationManager()
        )
        self._application_launcher = (
            application_launcher
            if application_launcher is not None
            else WindowsApplicationLauncher()
        )
        self._application_state_reader = (
            application_state_reader
            if application_state_reader is not None
            else WindowsApplicationStateReader()
        )
        self._clock = clock if clock is not None else UTCClock()
        self._permission_grants = permission_grants
        self._log_writer = log_writer
        self._log_path = log_path
        self._ai_provider = ai_provider

    def run(self) -> Configuration:
        """Initialize and return the foundation runtime configuration.

        Returns:
            The validated, immutable application configuration.
        """
        return self._configuration_provider.load()

    def compose(self) -> InteractiveRuntime:
        """Compose the production foreground runtime and load its capability.

        Returns:
            A request boundary backed by the complete production pipeline.
        """
        runtime, _ = self._compose_runtime()
        return runtime

    def compose_host(
        self,
        input_reader: InputReader = input,
        output_writer: OutputWriter = print,
    ) -> RuntimeHost:
        """Compose the production foreground host and interaction boundary.

        Args:
            input_reader: Foreground text input callable.
            output_writer: User-facing text output callable.

        Returns:
            A created Runtime Host backed by the production request pipeline.
        """
        runtime, event_bus = self._compose_runtime()
        console = InteractiveConsole(
            runtime.submit,
            input_reader=input_reader,
            output_writer=output_writer,
        )
        return RuntimeHost(console, event_bus)

    def _compose_runtime(
        self,
    ) -> tuple[InteractiveRuntime, InProcessEventBus]:
        configuration = self._configuration_provider.load()
        permission_grants = (
            self._permission_grants
            if self._permission_grants is not None
            else configuration.permission_grants
        )
        event_bus = InProcessEventBus()
        log_writer = (
            self._log_writer
            if self._log_writer is not None
            else JsonLinesLogWriter(
                self._log_path,
                configuration.log_level,
            )
        )
        EventLogObserver(log_writer).subscribe(event_bus)
        context_provider = UnavailableContextProvider(self._clock)
        working_memory = InMemoryWorkingMemory(
            self._clock,
            WorkingMemoryPolicy(
                capacity=configuration.working_memory_capacity,
                entry_ttl=timedelta(
                    seconds=configuration.working_memory_entry_ttl_seconds
                ),
            ),
        )
        confirmation_coordinator = InMemoryConfirmationCoordinator(
            self._clock,
            timedelta(seconds=configuration.confirmation_ttl_seconds),
        )
        conversation_history = InMemoryConversationHistory(
            self._clock,
            ConversationHistoryPolicy(
                max_exchanges=configuration.conversation_history_max_exchanges,
                max_characters=configuration.conversation_history_max_characters,
            ),
        )
        registry = InMemoryCapabilityRegistry(event_bus)
        ai_provider = self._compose_ai_provider(configuration, event_bus)
        capability_runtime = InProcessCapabilityRuntime(
            registry=registry,
            ai_availability_provider=ai_provider,
            cancellation=StaticCancellationSignal(),
            clock=self._clock,
            event_bus=event_bus,
        )
        capability_runtime.load(
            (
                OpenApplicationCapability(self._application_launcher),
                ApplicationStatusCapability(self._application_state_reader),
            )
        )
        ai_available = (
            configuration.ai_enabled
            and ai_provider.availability().state
            is AIProviderAvailabilityState.AVAILABLE
        )
        request_interpreter = (
            StructuredRequestInterpreter(
                ai_provider,
                registry,
                configuration.ai_timeout_seconds,
            )
            if ai_available
            else None
        )
        conversation_responder = ProviderBackedConversationResponder(
            ai_provider,
            registry,
            configuration.ai_timeout_seconds,
            conversation_history,
            self._clock,
        )
        started_at = self._clock.now()
        core = Core(
            event_bus=event_bus,
            request_classifier=DeterministicRequestClassifier(event_bus),
            capability_catalog=registry,
            decision_engine=DeterministicDecisionEngine(
                DecisionPolicy(_INTERACTIVE_V0_MINIMUM_CONFIDENCE),
                event_bus,
            ),
            planner=DeterministicPlanner(registry, self._clock, event_bus),
            capability_runtime=capability_runtime,
            context_provider=context_provider,
            memory_snapshot_provider=working_memory,
            platform_state=PlatformStateSnapshot(
                lifecycle_phase="RUNNING",
                operational_state=OperationalState.ACTIVE,
                performance_profile=PerformanceProfile.BALANCED,
                startup_at=started_at,
                latest_state_change_at=started_at,
            ),
            user_policy=UserPolicy(
                permission_grants=permission_grants,
                blocked_capability_ids=(),
                allow_interruption=True,
                allow_delegation=True,
                delegation_service_ids=(
                    (REQUEST_INTERPRETER_SERVICE_ID,) if ai_available else ()
                )
                + (CONVERSATION_RESPONDER_SERVICE_ID,),
            ),
            planning_constraints=PlanningConstraints(
                allowed_capability_ids=(
                    OPEN_APPLICATION_CAPABILITY_ID,
                    APPLICATION_STATUS_CAPABILITY_ID,
                ),
                blocked_capability_ids=(),
                maximum_steps=_INTERACTIVE_V0_MAXIMUM_PLAN_STEPS,
                deadline=None,
                require_confirmation=False,
            ),
            execution_timeout_seconds=None,
            confirmation_coordinator=confirmation_coordinator,
            interaction_language_resolver=(
                DeterministicInteractionLanguageResolver()
            ),
            request_interpreter=request_interpreter,
            conversation_responder=conversation_responder,
        )
        return InteractiveRuntime(core, self._clock), event_bus

    def _compose_ai_provider(
        self,
        configuration: Configuration,
        event_bus: InProcessEventBus,
    ) -> AIProvider:
        if not configuration.ai_enabled:
            return UnavailableAIAvailabilityProvider()
        if self._ai_provider is not None:
            return self._ai_provider
        if configuration.ai_provider == "ollama":
            return OllamaProvider(
                base_url=configuration.ollama_base_url,
                model_id=configuration.ollama_model,
                clock=self._clock,
                event_bus=event_bus,
            )
        api_key = os.environ.get("ATREUS_OPENAI_API_KEY")
        if api_key is None or not api_key.strip():
            return UnavailableAIAvailabilityProvider()
        try:
            from atreus.ai.openai_provider import OpenAIProvider
        except ImportError:
            return UnavailableAIAvailabilityProvider()
        return OpenAIProvider(
            api_key=api_key,
            model_id=configuration.ai_model,
            clock=self._clock,
            event_bus=event_bus,
        )
