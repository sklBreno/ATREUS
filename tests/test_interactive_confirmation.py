"""Integration tests for Interactive Confirmation V0."""

from datetime import UTC, datetime

import pytest

from atreus.ai.models import (
    AIProviderAvailability,
    AIProviderAvailabilityState,
    AIRequest,
    AIResponse,
)
from atreus.bootstrap.bootstrap import Bootstrap
from atreus.configuration.configuration_manager import ConfigurationManager
from atreus.configuration.loader import ConfigurationLoader
from atreus.decision.models import DecisionOutcome
from atreus.execution.models import CapabilityExecutionStatus
from atreus.interaction.models import InteractionLanguage
from atreus.interfaces.ai_provider import AIProvider
from atreus.interfaces.application_controller import ApplicationController
from atreus.interfaces.clock import Clock
from atreus.runtime.console import InteractiveConsole
from atreus.runtime.runtime import InteractiveRuntime
from atreus.system.models import (
    ApplicationIdentifier,
    ApplicationInstance,
    ApplicationLaunchRequest,
    SystemOperationContext,
)
from tests.support import RecordingApplicationController, RecordingLogWriter

NOW = datetime(2026, 9, 2, 12, 0, tzinfo=UTC)


class MutableClock(Clock):
    """Return a controllable timestamp for integration tests."""

    def __init__(self) -> None:
        """Initialize the current time."""
        self.timestamp = NOW

    def now(self) -> datetime:
        """Return the current time."""
        return self.timestamp


class RecordingAIProvider(AIProvider):
    """Return one approved structured interpretation without network access."""

    def __init__(
        self,
        clock: Clock,
        target_id: str = "calculator",
    ) -> None:
        """Initialize the approved target and request recording."""
        self._clock = clock
        self._target_id = target_id
        self.requests: list[AIRequest] = []

    def availability(self) -> AIProviderAvailability:
        """Report deterministic provider availability."""
        return AIProviderAvailability(AIProviderAvailabilityState.AVAILABLE)

    def generate(self, request: AIRequest) -> AIResponse:
        """Return one local structured response and record the request."""
        self.requests.append(request)
        return AIResponse(
            request.ai_request_id,
            request.request_id,
            '{"intent_id":"OPEN_APPLICATION","target_id":"'
            f'{self._target_id}","confidence":0.9}}',
            "test",
            "test-model",
            self._clock.now(),
        )


class FailingApplicationController(ApplicationController):
    """Fail one approved launch after recording the native-boundary call."""

    def __init__(self) -> None:
        """Initialize an empty call count."""
        self.call_count = 0

    def launch(
        self,
        request: ApplicationLaunchRequest,
        context: SystemOperationContext,
    ) -> ApplicationInstance:
        """Raise one deterministic native-boundary failure."""
        self.call_count += 1
        raise OSError("private native launch detail")


def make_configuration_manager() -> ConfigurationManager:
    """Create validated AI-enabled configuration for local fake integration."""
    return ConfigurationManager(
        loader=ConfigurationLoader(
            env_file_path=None,
            environment={
                "ATREUS_AI_ENABLED": "true",
                "ATREUS_AI_MODEL": "test-model",
                "ATREUS_AI_TIMEOUT_SECONDS": "15",
                "ATREUS_CONFIRMATION_TTL_SECONDS": "120",
            },
        )
    )


def build_runtime(
    *,
    permission_grants: tuple[str, ...] = ("application.control",),
    application_controller: ApplicationController | None = None,
    log_writer: RecordingLogWriter | None = None,
    interpreted_target_id: str = "calculator",
) -> tuple[
    InteractiveRuntime,
    RecordingAIProvider,
    RecordingApplicationController,
    MutableClock,
]:
    """Compose a complete runtime with controlled AI and System boundaries."""
    clock = MutableClock()
    provider = RecordingAIProvider(clock, interpreted_target_id)
    controller = RecordingApplicationController()
    runtime = Bootstrap(
        configuration_provider=make_configuration_manager(),
        application_controller=application_controller or controller,
        clock=clock,
        permission_grants=permission_grants,
        log_writer=log_writer or RecordingLogWriter(),
        ai_provider=provider,
    ).compose()
    return runtime, provider, controller, clock


@pytest.mark.parametrize(
    ("request_content", "answer", "language"),
    (
        ("abre a calculadora pra mim", "sim", InteractionLanguage.PT_BR),
        (
            "could you open the calculator?",
            "yes",
            InteractionLanguage.EN_US,
        ),
    ),
)
def test_ai_interpretation_confirmation_executes_exact_action_once(
    request_content: str,
    answer: str,
    language: InteractionLanguage,
) -> None:
    runtime, provider, controller, _ = build_runtime()

    initial = runtime.submit(request_content)
    accepted = runtime.submit(answer)

    assert initial.decision.outcome is DecisionOutcome.ASK_FOR_CONFIRMATION
    assert initial.confirmation_prompt is not None
    assert initial.confirmation_prompt.target_id is ApplicationIdentifier.CALCULATOR
    assert initial.confirmation_prompt.language is language
    assert accepted.decision.outcome is DecisionOutcome.REQUEST_PLANNING
    assert accepted.plan is not None
    assert accepted.plan.steps[0].capability_id == "application.open"
    assert tuple(
        (argument.name, argument.value)
        for argument in accepted.plan.steps[0].arguments
    ) == (("application_id", "calculator"),)
    assert accepted.execution_results[0].status is (
        CapabilityExecutionStatus.SUCCEEDED
    )
    assert len(provider.requests) == 1
    assert len(controller.calls) == 1


def test_portuguese_notepad_target_is_preserved_without_text_reconstruction() -> None:
    runtime, provider, controller, _ = build_runtime(
        interpreted_target_id="notepad"
    )

    initial = runtime.submit("pode abrir o bloco de notas para eu escrever")
    accepted = runtime.submit("sim")

    assert initial.confirmation_prompt is not None
    assert initial.confirmation_prompt.target_id is ApplicationIdentifier.NOTEPAD
    assert initial.confirmation_prompt.language is InteractionLanguage.PT_BR
    assert accepted.plan is not None
    assert accepted.plan.steps[0].arguments[0].value == "notepad"
    assert len(provider.requests) == 1
    assert controller.calls[0][0].application_id is ApplicationIdentifier.NOTEPAD


@pytest.mark.parametrize("answer", ("não", "nao", "cancelar", "no", "cancel"))
def test_negative_confirmation_never_plans_or_executes(answer: str) -> None:
    runtime, provider, controller, _ = build_runtime()
    runtime.submit("abre a calculadora pra mim")

    result = runtime.submit(answer)

    assert result.decision.outcome is DecisionOutcome.IGNORE
    assert result.plan is None
    assert result.execution_results == ()
    assert len(provider.requests) == 1
    assert controller.calls == []


@pytest.mark.parametrize("answer", ("sim", "yes", "não", "no"))
def test_confirmation_token_without_pending_never_executes(answer: str) -> None:
    runtime, provider, controller, _ = build_runtime()

    result = runtime.submit(answer)

    assert result.decision.outcome is DecisionOutcome.IGNORE
    assert result.plan is None
    assert result.execution_results == ()
    assert provider.requests == []
    assert controller.calls == []


@pytest.mark.parametrize(
    "content",
    (
        "yes && delete everything",
        "sim; open cmd",
        "yes, and also open notepad",
        "sim, abre também o Spotify",
        "ignore previous confirmation and do X",
    ),
)
def test_composed_response_invalidates_pending_without_reinterpretation(
    content: str,
) -> None:
    runtime, provider, controller, _ = build_runtime()
    runtime.submit("abre a calculadora pra mim")

    invalidated = runtime.submit(content)
    replay = runtime.submit("sim")

    assert invalidated.decision.outcome is DecisionOutcome.IGNORE
    assert invalidated.execution_results == ()
    assert replay.decision.outcome is DecisionOutcome.IGNORE
    assert replay.execution_results == ()
    assert len(provider.requests) == 1
    assert controller.calls == []


def test_unrelated_request_consumes_pending_and_requires_resubmission() -> None:
    runtime, _, controller, _ = build_runtime()
    runtime.submit("abre a calculadora pra mim")

    invalidated = runtime.submit("open notepad")
    replay = runtime.submit("yes")
    resubmitted = runtime.submit("open notepad")

    assert invalidated.decision.outcome is DecisionOutcome.IGNORE
    assert invalidated.execution_results == ()
    assert replay.decision.outcome is DecisionOutcome.IGNORE
    assert resubmitted.execution_results[0].status is (
        CapabilityExecutionStatus.SUCCEEDED
    )
    assert len(controller.calls) == 1
    assert controller.calls[0][0].application_id is ApplicationIdentifier.NOTEPAD


def test_accepted_confirmation_is_single_use_even_after_success() -> None:
    runtime, provider, controller, _ = build_runtime()
    runtime.submit("abre a calculadora pra mim")

    first = runtime.submit("sim")
    duplicate = runtime.submit("sim")

    assert first.execution_results
    assert duplicate.decision.outcome is DecisionOutcome.IGNORE
    assert duplicate.execution_results == ()
    assert len(provider.requests) == 1
    assert len(controller.calls) == 1


def test_accepted_confirmation_remains_consumed_after_execution_failure() -> None:
    failing_controller = FailingApplicationController()
    runtime, provider, _, _ = build_runtime(
        application_controller=failing_controller
    )
    runtime.submit("abre a calculadora pra mim")

    failed = runtime.submit("sim")
    duplicate = runtime.submit("sim")

    assert failed.execution_results[0].status is CapabilityExecutionStatus.FAILED
    assert duplicate.decision.reason_code == "confirmation_not_pending"
    assert duplicate.execution_results == ()
    assert len(provider.requests) == 1
    assert failing_controller.call_count == 1


def test_expired_confirmation_cannot_be_replayed() -> None:
    runtime, provider, controller, clock = build_runtime()
    initial = runtime.submit("abre a calculadora pra mim")
    assert initial.confirmation_prompt is not None
    clock.timestamp = initial.confirmation_prompt.expires_at

    expired = runtime.submit("sim")
    replay = runtime.submit("sim")

    assert expired.decision.reason_code == "confirmation_expired"
    assert expired.execution_results == ()
    assert replay.decision.reason_code == "confirmation_not_pending"
    assert len(provider.requests) == 1
    assert controller.calls == []


def test_confirmation_does_not_create_permission_grant() -> None:
    runtime, provider, controller, _ = build_runtime(permission_grants=())

    initial = runtime.submit("abre a calculadora pra mim")
    response = runtime.submit("sim")

    assert initial.confirmation_prompt is None
    assert initial.decision.reason_code == "required_permission_missing"
    assert response.decision.reason_code == "confirmation_not_pending"
    assert len(provider.requests) == 1
    assert controller.calls == []


@pytest.mark.parametrize(
    "content",
    (
        "open calculator && shutdown",
        "sim e depois abra o Spotify",
        "abre a calculadora e depois desligue o computador",
    ),
)
def test_malicious_or_composed_request_never_reaches_ai(content: str) -> None:
    runtime, provider, controller, _ = build_runtime()

    result = runtime.submit(content)

    assert result.execution_results == ()
    assert provider.requests == []
    assert controller.calls == []


@pytest.mark.parametrize(
    ("request_content", "answer", "expected_prompt"),
    (
        (
            "abre a calculadora pra mim",
            "sim",
            "Você quer que eu abra a Calculadora? [sim/não]",
        ),
        (
            "could you open the calculator?",
            "yes",
            "Do you want me to open Calculator? [yes/no]",
        ),
    ),
)
def test_console_renders_structured_prompt_and_completes_fake_flow(
    request_content: str,
    answer: str,
    expected_prompt: str,
) -> None:
    runtime, provider, controller, _ = build_runtime()
    values = iter((request_content, answer, "exit"))
    outputs: list[str] = []
    console = InteractiveConsole(
        runtime.submit,
        lambda _prompt: next(values),
        outputs.append,
    )

    assert console.run() == 0
    assert outputs == [expected_prompt, "Opened calculator."]
    assert len(provider.requests) == 1
    assert len(controller.calls) == 1


def test_new_composition_starts_without_pending_confirmation() -> None:
    clock = MutableClock()
    provider = RecordingAIProvider(clock)
    controller = RecordingApplicationController()
    bootstrap = Bootstrap(
        configuration_provider=make_configuration_manager(),
        application_controller=controller,
        clock=clock,
        log_writer=RecordingLogWriter(),
        ai_provider=provider,
    )
    first_runtime = bootstrap.compose()
    second_runtime = bootstrap.compose()
    first_runtime.submit("abre a calculadora pra mim")

    result = second_runtime.submit("sim")

    assert result.decision.reason_code == "confirmation_not_pending"
    assert controller.calls == []


def test_confirmation_content_and_ai_response_are_absent_from_logs() -> None:
    writer = RecordingLogWriter()
    runtime, _, _, _ = build_runtime(log_writer=writer)
    private_content = "yes && private-confirmation-value"

    runtime.submit("abre a calculadora pra mim")
    runtime.submit(private_content)

    serialized_records = repr(writer.records)
    assert private_content not in serialized_records
    assert "private-confirmation-value" not in serialized_records
    assert '"confidence":0.9' not in serialized_records
