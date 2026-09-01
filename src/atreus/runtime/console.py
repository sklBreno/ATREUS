"""Synchronous foreground console for the ATREUS local runtime."""

from collections.abc import Callable

from atreus.core.models import CoreRequestResult
from atreus.decision.models import DecisionOutcome
from atreus.execution.models import CapabilityExecutionStatus
from atreus.interfaces.foreground_interface import ForegroundInterface
from atreus.system.models import ApplicationIdentifier

type RequestHandler = Callable[[str], CoreRequestResult]
type InputReader = Callable[[str], str]
type OutputWriter = Callable[[str], None]

_EXIT_COMMANDS = frozenset({"exit", "quit"})


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
        successful_outputs = tuple(
            item
            for execution in result.execution_results
            if execution.status is CapabilityExecutionStatus.SUCCEEDED
            and execution.output is not None
            for item in execution.output
        )
        output_values = {item.name: item.value for item in successful_outputs}
        application_id = output_values.get("application_id")
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
