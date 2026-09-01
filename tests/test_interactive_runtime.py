"""Tests for the production foreground ATREUS runtime and console."""

from pathlib import Path

import pytest

from atreus.__main__ import main
from atreus.bootstrap.bootstrap import Bootstrap
from atreus.runtime.console import InteractiveConsole
from atreus.system.windows_application_controller import (
    WindowsApplicationController,
)
from tests.support import (
    FixedClock,
    RecordingApplicationController,
    RecordingLogWriter,
)


class InputSequence:
    """Return a deterministic sequence of foreground input values."""

    def __init__(self, values: tuple[str, ...]) -> None:
        """Initialize the ordered input values."""
        self._values = iter(values)
        self.prompts: list[str] = []

    def __call__(self, prompt: str) -> str:
        """Return the next value while recording the displayed prompt."""
        self.prompts.append(prompt)
        return next(self._values)


def build_console(
    inputs: tuple[str, ...],
    *,
    controller: RecordingApplicationController | None = None,
) -> tuple[InteractiveConsole, InputSequence, list[str]]:
    """Compose a production console with controlled system and I/O boundaries."""
    runtime = Bootstrap(
        application_controller=controller or RecordingApplicationController(),
        clock=FixedClock(),
        log_writer=RecordingLogWriter(),
    ).compose()
    input_reader = InputSequence(inputs)
    outputs: list[str] = []
    console = InteractiveConsole(runtime.submit, input_reader, outputs.append)
    return console, input_reader, outputs


@pytest.mark.parametrize("application_id", ("calculator", "notepad", "spotify"))
def test_console_formats_approved_application_success(
    application_id: str,
) -> None:
    controller = RecordingApplicationController()
    console, input_reader, outputs = build_console(
        (f"open {application_id}", "exit"),
        controller=controller,
    )

    exit_status = console.run()

    assert exit_status == 0
    assert input_reader.prompts == ["ATREUS > ", "ATREUS > "]
    assert outputs == [f"Opened {application_id}."]
    assert len(controller.calls) == 1


@pytest.mark.parametrize(
    "content",
    (
        "open calculator && shutdown",
        "open notepad && calc",
        "open spotify && anything",
        "open calculator please run shutdown",
        "shutdown computer",
        "arbitrary text",
    ),
)
def test_console_does_not_execute_unrelated_requests(content: str) -> None:
    controller = RecordingApplicationController()
    console, _, outputs = build_console(
        (content, "quit"),
        controller=controller,
    )

    assert console.run() == 0

    assert outputs == ["I need clarification before I can act."]
    assert controller.calls == []


def test_production_flow_reports_unmapped_spotify_without_process_start() -> None:
    commands: list[tuple[str, ...]] = []

    def start_process(command: tuple[str, ...]) -> int:
        commands.append(command)
        return 4321

    controller = WindowsApplicationController(start_process, "win32")
    console, _, outputs = build_console(
        ("open spotify", "exit"),
        controller=controller,
    )

    assert console.run() == 0
    assert outputs == ["Unable to complete the request."]
    assert commands == []


@pytest.mark.parametrize("command", ("exit", "quit", " EXIT "))
def test_console_exits_without_submitting_a_request(command: str) -> None:
    submitted: list[str] = []
    console = InteractiveConsole(
        lambda content: submitted.append(content),  # type: ignore[arg-type]
        InputSequence((command,)),
        lambda output: None,
    )

    assert console.run() == 0
    assert submitted == []


@pytest.mark.parametrize("error_type", (EOFError, KeyboardInterrupt))
def test_console_exits_cleanly_when_input_stops(
    error_type: type[BaseException],
) -> None:
    def stop_input(prompt: str) -> str:
        raise error_type

    console = InteractiveConsole(
        lambda content: pytest.fail("Request handler must not be called."),
        stop_input,
        lambda output: pytest.fail("Output writer must not be called."),
    )

    assert console.run() == 0


def test_console_sanitizes_pipeline_failures() -> None:
    inputs = InputSequence(("open calculator", "exit"))
    outputs: list[str] = []

    def fail_request(content: str) -> None:
        raise RuntimeError("private runtime detail")

    console = InteractiveConsole(
        fail_request,  # type: ignore[arg-type]
        inputs,
        outputs.append,
    )

    assert console.run() == 0
    assert outputs == ["Unable to process the request."]


def test_console_exits_cleanly_when_processing_is_interrupted() -> None:
    def interrupt_request(content: str) -> None:
        raise KeyboardInterrupt

    console = InteractiveConsole(
        interrupt_request,  # type: ignore[arg-type]
        InputSequence(("open calculator",)),
        lambda output: pytest.fail("Output writer must not be called."),
    )

    assert console.run() == 0


def test_entrypoint_starts_and_exits_without_launching_an_application() -> None:
    outputs: list[str] = []
    bootstrap = Bootstrap(
        application_controller=RecordingApplicationController(),
        clock=FixedClock(),
        log_writer=RecordingLogWriter(),
    )

    assert main(lambda prompt: "exit", outputs.append, bootstrap) == 0
    assert outputs == []


def test_production_source_does_not_import_test_modules() -> None:
    source_files = tuple(Path("src").rglob("*.py"))

    assert source_files
    for source_file in source_files:
        source = source_file.read_text(encoding="utf-8")
        assert "from tests" not in source
        assert "import tests" not in source
