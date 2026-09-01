"""Production dependency composition for the ATREUS local runtime."""

from pathlib import Path

from atreus.ai.unavailable_availability import UnavailableAIAvailabilityProvider
from atreus.capability.contracts import OPEN_APPLICATION_CAPABILITY_ID
from atreus.capability.open_application import OpenApplicationCapability
from atreus.capability.registry import InMemoryCapabilityRegistry
from atreus.configuration.configuration import Configuration
from atreus.configuration.configuration_manager import ConfigurationManager
from atreus.context.unavailable_context import UnavailableContextProvider
from atreus.core.core import Core
from atreus.decision.decision_engine import DeterministicDecisionEngine
from atreus.decision.models import DecisionPolicy, UserPolicy
from atreus.events.event_bus import InProcessEventBus
from atreus.execution.runtime import InProcessCapabilityRuntime
from atreus.interfaces.application_controller import ApplicationController
from atreus.interfaces.clock import Clock
from atreus.interfaces.configuration import ConfigurationProvider
from atreus.interfaces.log_writer import LogWriter
from atreus.logging.event_observer import EventLogObserver
from atreus.logging.jsonl_writer import JsonLinesLogWriter
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
from atreus.system.models import APPLICATION_CONTROL_PERMISSION
from atreus.system.windows_application_controller import WindowsApplicationController

_INTERACTIVE_V0_PERMISSION_GRANTS = (APPLICATION_CONTROL_PERMISSION,)
_INTERACTIVE_V0_MINIMUM_CONFIDENCE = 0.5
_INTERACTIVE_V0_MAXIMUM_PLAN_STEPS = 1
_OBSERVABILITY_V0_LOG_PATH = Path("logs/atreus.log")


class Bootstrap:
    """Compose the concrete dependencies required by the local runtime."""

    def __init__(
        self,
        configuration_provider: ConfigurationProvider | None = None,
        application_controller: ApplicationController | None = None,
        clock: Clock | None = None,
        permission_grants: tuple[str, ...] = _INTERACTIVE_V0_PERMISSION_GRANTS,
        log_writer: LogWriter | None = None,
        log_path: Path = _OBSERVABILITY_V0_LOG_PATH,
    ) -> None:
        """Initialize Bootstrap with injectable infrastructure boundaries.

        Args:
            configuration_provider: Provider for the validated application
                configuration.
            application_controller: Controlled desktop application boundary.
            clock: Time source shared by production runtime components.
            permission_grants: Explicit grants supplied to Runtime enforcement.
            log_writer: Optional injected structured logging boundary.
            log_path: Local JSON Lines destination used by the default writer.
        """
        self._configuration_provider = (
            configuration_provider
            if configuration_provider is not None
            else ConfigurationManager()
        )
        self._application_controller = (
            application_controller
            if application_controller is not None
            else WindowsApplicationController()
        )
        self._clock = clock if clock is not None else UTCClock()
        self._permission_grants = permission_grants
        self._log_writer = log_writer
        self._log_path = log_path

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
        registry = InMemoryCapabilityRegistry(event_bus)
        capability_runtime = InProcessCapabilityRuntime(
            registry=registry,
            ai_availability_provider=UnavailableAIAvailabilityProvider(),
            cancellation=StaticCancellationSignal(),
            clock=self._clock,
            event_bus=event_bus,
        )
        capability_runtime.load(
            (OpenApplicationCapability(self._application_controller),)
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
            platform_state=PlatformStateSnapshot(
                lifecycle_phase="RUNNING",
                operational_state=OperationalState.ACTIVE,
                performance_profile=PerformanceProfile.BALANCED,
                startup_at=started_at,
                latest_state_change_at=started_at,
            ),
            user_policy=UserPolicy(
                permission_grants=self._permission_grants,
                blocked_capability_ids=(),
                allow_interruption=True,
                allow_delegation=False,
            ),
            planning_constraints=PlanningConstraints(
                allowed_capability_ids=(OPEN_APPLICATION_CAPABILITY_ID,),
                blocked_capability_ids=(),
                maximum_steps=_INTERACTIVE_V0_MAXIMUM_PLAN_STEPS,
                deadline=None,
                require_confirmation=False,
            ),
            execution_timeout_seconds=None,
        )
        return InteractiveRuntime(core, self._clock), event_bus
