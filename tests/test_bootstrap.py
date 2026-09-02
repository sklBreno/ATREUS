"""Integration tests for the ATREUS foundation Bootstrap."""

from datetime import timedelta

import pytest

from atreus.ai.models import (
    AIProviderAvailability,
    AIProviderAvailabilityState,
    AIRequest,
    AIResponse,
)
from atreus.bootstrap.bootstrap import Bootstrap
from atreus.configuration.configuration import Configuration
from atreus.configuration.configuration_manager import ConfigurationManager
from atreus.configuration.loader import ConfigurationLoader
from atreus.decision.models import DecisionOutcome
from atreus.execution.models import CapabilityExecutionStatus
from atreus.interfaces.ai_provider import AIProvider
from atreus.interfaces.clock import Clock
from atreus.memory.models import MemorySnapshot, MemoryValue, WorkingMemoryPolicy
from atreus.memory.working_memory import InMemoryWorkingMemory
from tests.support import (
    NOW,
    FixedClock,
    RecordingApplicationController,
    RecordingLogWriter,
)


class BootstrapAIProvider(AIProvider):
    """Return one structured interpretation without external access."""

    def __init__(self) -> None:
        """Initialize an empty request collection."""
        self.requests: list[AIRequest] = []

    def availability(self) -> AIProviderAvailability:
        """Report deterministic test availability."""
        return AIProviderAvailability(AIProviderAvailabilityState.AVAILABLE)

    def generate(self, request: AIRequest) -> AIResponse:
        """Record and return one approved structured response."""
        self.requests.append(request)
        return AIResponse(
            request.ai_request_id,
            request.request_id,
            '{"intent_id":"OPEN_APPLICATION","target_id":"calculator",'
            '"confidence":0.9}',
            "test",
            "test-model",
            NOW,
        )


def make_ai_configuration_manager(*, enabled: bool) -> ConfigurationManager:
    """Create validated AI composition settings without secrets."""
    return ConfigurationManager(
        loader=ConfigurationLoader(
            env_file_path=None,
            environment={
                "ATREUS_AI_ENABLED": str(enabled).lower(),
                "ATREUS_AI_MODEL": "test-model",
                "ATREUS_AI_TIMEOUT_SECONDS": "10",
            },
        )
    )


def test_bootstrap_runs_configuration_foundation_flow() -> None:
    loader = ConfigurationLoader(
        env_file_path=None,
        environment={"ATREUS_DEBUG": "false"},
    )
    manager = ConfigurationManager(loader=loader)

    configuration = Bootstrap(configuration_provider=manager).run()

    assert isinstance(configuration, Configuration)
    assert configuration.debug is False


def test_bootstrap_composes_complete_production_runtime() -> None:
    controller = RecordingApplicationController(process_id=2468)
    runtime = Bootstrap(
        application_controller=controller,
        clock=FixedClock(),
        log_writer=RecordingLogWriter(),
    ).compose()

    result = runtime.submit("open calculator")

    assert result.request_id == result.classification.request_id
    assert result.request_id == result.decision.request_id
    assert result.decision.outcome is DecisionOutcome.REQUEST_PLANNING
    assert result.plan is not None
    assert result.plan.request_id == result.request_id
    assert len(result.execution_results) == 1
    assert (
        result.execution_results[0].status
        is CapabilityExecutionStatus.SUCCEEDED
    )
    assert len(controller.calls) == 1


def test_bootstrap_does_not_bypass_runtime_permission_enforcement() -> None:
    controller = RecordingApplicationController()
    runtime = Bootstrap(
        application_controller=controller,
        clock=FixedClock(),
        permission_grants=(),
        log_writer=RecordingLogWriter(),
    ).compose()

    result = runtime.submit("open calculator")

    assert result.decision.outcome is DecisionOutcome.IGNORE
    assert result.decision.reason_code == "required_permission_missing"
    assert result.execution_results == ()
    assert controller.calls == []


def test_bootstrap_keeps_one_memory_store_per_composition(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class RecordingWorkingMemory(InMemoryWorkingMemory):
        """Record snapshots captured by one composed runtime."""

        def __init__(self, clock: Clock, policy: WorkingMemoryPolicy) -> None:
            """Initialize the recording store."""
            super().__init__(clock, policy)
            self.snapshots: list[MemorySnapshot] = []

        def snapshot(self) -> MemorySnapshot:
            """Record and return one stable memory snapshot."""
            snapshot = super().snapshot()
            self.snapshots.append(snapshot)
            return snapshot

    stores: list[RecordingWorkingMemory] = []
    policies: list[WorkingMemoryPolicy] = []

    def create_store(
        clock: Clock,
        policy: WorkingMemoryPolicy,
    ) -> RecordingWorkingMemory:
        store = RecordingWorkingMemory(clock, policy)
        stores.append(store)
        policies.append(policy)
        return store

    monkeypatch.setattr(
        "atreus.bootstrap.bootstrap.InMemoryWorkingMemory",
        create_store,
    )
    bootstrap = Bootstrap(
        application_controller=RecordingApplicationController(),
        clock=FixedClock(),
        log_writer=RecordingLogWriter(),
    )
    first_runtime = bootstrap.compose()
    first_store = stores[0]
    remembered = first_store.remember(
        "tests.recent_action",
        (MemoryValue("application_id", "calculator"),),
        "tests",
    )

    first_runtime.submit("arbitrary text")
    first_runtime.submit("arbitrary text")

    assert policies[0] == WorkingMemoryPolicy(
        64,
        timedelta(seconds=1800),
    )
    assert len(first_store.snapshots) == 2
    assert all(
        snapshot.entries == (remembered,)
        for snapshot in first_store.snapshots
    )

    second_runtime = bootstrap.compose()
    second_runtime.submit("arbitrary text")

    assert len(stores) == 2
    assert stores[1] is not first_store
    assert stores[1].snapshots[0].entries == ()


def test_bootstrap_ai_interpretation_requires_confirmation_without_execution() -> None:
    provider = BootstrapAIProvider()
    controller = RecordingApplicationController()
    runtime = Bootstrap(
        configuration_provider=make_ai_configuration_manager(enabled=True),
        application_controller=controller,
        ai_provider=provider,
        clock=FixedClock(),
        log_writer=RecordingLogWriter(),
    ).compose()

    result = runtime.submit("Please open calculator for me")

    assert len(provider.requests) == 1
    assert result.decision.outcome is DecisionOutcome.ASK_FOR_CONFIRMATION
    assert result.plan is None
    assert result.execution_results == ()
    assert controller.calls == []


@pytest.mark.parametrize("content", ("open calculator", "open notepad"))
def test_bootstrap_deterministic_fast_path_makes_zero_ai_calls(
    content: str,
) -> None:
    provider = BootstrapAIProvider()
    runtime = Bootstrap(
        configuration_provider=make_ai_configuration_manager(enabled=True),
        application_controller=RecordingApplicationController(),
        ai_provider=provider,
        clock=FixedClock(),
        log_writer=RecordingLogWriter(),
    ).compose()

    result = runtime.submit(content)

    assert result.execution_results[0].status is CapabilityExecutionStatus.SUCCEEDED
    assert provider.requests == []


def test_bootstrap_missing_credential_keeps_ai_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("ATREUS_OPENAI_API_KEY", raising=False)
    controller = RecordingApplicationController()
    runtime = Bootstrap(
        configuration_provider=make_ai_configuration_manager(enabled=True),
        application_controller=controller,
        clock=FixedClock(),
        log_writer=RecordingLogWriter(),
    ).compose()

    result = runtime.submit("Please open calculator for me")

    assert result.decision.outcome is DecisionOutcome.ASK_FOR_CONFIRMATION
    assert result.execution_results == ()
    assert controller.calls == []


def test_bootstrap_disabled_ai_ignores_injected_provider() -> None:
    provider = BootstrapAIProvider()
    runtime = Bootstrap(
        configuration_provider=make_ai_configuration_manager(enabled=False),
        application_controller=RecordingApplicationController(),
        ai_provider=provider,
        clock=FixedClock(),
        log_writer=RecordingLogWriter(),
    ).compose()

    runtime.submit("Please open calculator for me")

    assert provider.requests == []
