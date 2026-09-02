"""Synchronous foreground console for the ATREUS local runtime."""

from collections.abc import Callable

from atreus.core.models import CoreRequestResult
from atreus.decision.models import DecisionOutcome
from atreus.execution.models import CapabilityExecutionStatus
from atreus.interaction.models import InteractionLanguage
from atreus.interfaces.foreground_interface import ForegroundInterface
from atreus.system.models import ApplicationIdentifier, ApplicationState

type RequestHandler = Callable[[str], CoreRequestResult]
type InputReader = Callable[[str], str]
type OutputWriter = Callable[[str], None]

_EXIT_COMMANDS = frozenset({"exit", "quit"})
_APPLICATION_DISPLAY_NAMES = {
    InteractionLanguage.PT_BR: {
        ApplicationIdentifier.CALCULATOR: "Calculadora",
        ApplicationIdentifier.NOTEPAD: "Bloco de Notas",
        ApplicationIdentifier.SPOTIFY: "Spotify",
    },
    InteractionLanguage.EN_US: {
        ApplicationIdentifier.CALCULATOR: "Calculator",
        ApplicationIdentifier.NOTEPAD: "Notepad",
        ApplicationIdentifier.SPOTIFY: "Spotify",
    },
}
_PT_BR_CONFIRMATION_TARGETS = {
    ApplicationIdentifier.CALCULATOR: "a Calculadora",
    ApplicationIdentifier.NOTEPAD: "o Bloco de Notas",
    ApplicationIdentifier.SPOTIFY: "o Spotify",
}
_APPLICATION_STATUS_MESSAGES = {
    InteractionLanguage.PT_BR: {
        ApplicationIdentifier.CALCULATOR: {
            ApplicationState.RUNNING: "A Calculadora está aberta.",
            ApplicationState.NOT_RUNNING: "A Calculadora não está aberta.",
            ApplicationState.UNKNOWN: (
                "Não foi possível determinar o estado da Calculadora."
            ),
        },
        ApplicationIdentifier.NOTEPAD: {
            ApplicationState.RUNNING: "O Bloco de Notas está aberto.",
            ApplicationState.NOT_RUNNING: "O Bloco de Notas não está aberto.",
            ApplicationState.UNKNOWN: (
                "Não foi possível determinar o estado do Bloco de Notas."
            ),
        },
    },
    InteractionLanguage.EN_US: {
        ApplicationIdentifier.CALCULATOR: {
            ApplicationState.RUNNING: "Calculator is open.",
            ApplicationState.NOT_RUNNING: "Calculator is not open.",
            ApplicationState.UNKNOWN: "Could not determine Calculator status.",
        },
        ApplicationIdentifier.NOTEPAD: {
            ApplicationState.RUNNING: "Notepad is open.",
            ApplicationState.NOT_RUNNING: "Notepad is not open.",
            ApplicationState.UNKNOWN: "Could not determine Notepad status.",
        },
    },
}


class InteractiveConsole(ForegroundInterface):
    """Read foreground text requests and display sanitized runtime results."""

    def __init__(
        self,
        request_handler: RequestHandler,
        input_reader: InputReader = input,
        output_writer: OutputWriter = print,
    ) -> None:
        """Initialize the console with injectable interaction boundaries.

        Args:
            request_handler: Production text-request submission callable.
            input_reader: Foreground text input callable.
            output_writer: User-facing text output callable.
        """
        self._request_handler = request_handler
        self._input_reader = input_reader
        self._output_writer = output_writer

    def run(self) -> int:
        """Process requests until the user exits or input becomes unavailable.

        Returns:
            The successful process exit status.
        """
        while True:
            try:
                content = self._input_reader("ATREUS > ")
            except (EOFError, KeyboardInterrupt):
                return 0

            normalized_content = content.strip()
            if normalized_content.casefold() in _EXIT_COMMANDS:
                return 0
            if not normalized_content:
                continue

            try:
                result = self._request_handler(normalized_content)
            except KeyboardInterrupt:
                return 0
            except Exception:
                self._output_writer("Unable to process the request.")
                continue

            self._output_writer(self._format_result(result))

    @staticmethod
    def _format_result(result: CoreRequestResult) -> str:
        prompt = result.confirmation_prompt
        if prompt is not None:
            application_name = _APPLICATION_DISPLAY_NAMES[prompt.language][
                prompt.target_id
            ]
            if prompt.language is InteractionLanguage.EN_US:
                return f"Do you want me to open {application_name}? [yes/no]"
            target = _PT_BR_CONFIRMATION_TARGETS[prompt.target_id]
            return f"Você quer que eu abra {target}? [sim/não]"
        successful_outputs = tuple(
            item
            for execution in result.execution_results
            if execution.status is CapabilityExecutionStatus.SUCCEEDED
            and execution.output is not None
            for item in execution.output
        )
        output_values = {item.name: item.value for item in successful_outputs}
        application_id = output_values.get("application_id")
        application_state = output_values.get("state")
        if isinstance(application_id, str) and isinstance(application_state, str):
            try:
                approved_application = ApplicationIdentifier(application_id)
                approved_state = ApplicationState(application_state)
                messages = _APPLICATION_STATUS_MESSAGES[
                    result.interaction_language
                ][approved_application]
            except (KeyError, ValueError):
                pass
            else:
                return messages[approved_state]
        if (
            output_values.get("status") == "launched"
            and isinstance(application_id, str)
        ):
            try:
                approved_application = ApplicationIdentifier(application_id)
            except ValueError:
                pass
            else:
                return f"Opened {approved_application.value}."
        if result.execution_results:
            return "Unable to complete the request."
        if result.decision.outcome is DecisionOutcome.ASK_FOR_CONFIRMATION:
            return "I need clarification before I can act."
        if result.decision.outcome is DecisionOutcome.IGNORE:
            return "That action is not available."
        if result.decision.outcome is DecisionOutcome.SUGGEST:
            return "No action was taken."
        if result.decision.outcome is DecisionOutcome.DELEGATE:
            return "That request requires an unavailable service."
        return "Confirmation is required before I can act."
