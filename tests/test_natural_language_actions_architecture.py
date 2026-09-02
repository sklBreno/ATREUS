"""Architecture guards for Natural Language Actions V1."""

from pathlib import Path

from atreus.application.models import ApplicationIntent

ROOT = Path(__file__).parents[1]


def _read_source(relative_path: str) -> str:
    """Read one source module for a narrow architecture assertion."""
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_v1_exposes_only_open_and_status_application_intents() -> None:
    assert tuple(ApplicationIntent) == (
        ApplicationIntent.OPEN_APPLICATION,
        ApplicationIntent.APPLICATION_STATUS,
    )


def test_application_domain_contains_no_native_execution_details() -> None:
    source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (ROOT / "src/atreus/application").glob("*.py")
    ).casefold()

    assert "subprocess" not in source
    assert "calc.exe" not in source
    assert "notepad.exe" not in source
    assert "tasklist.exe" not in source
    assert "shell=true" not in source


def test_registry_contains_no_windows_application_identity() -> None:
    source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (ROOT / "src/atreus/capability").glob("registry.py")
    ).casefold()

    assert ".exe" not in source
    assert "process_name" not in source
    assert "subprocess" not in source


def test_runtime_and_system_layers_do_not_depend_on_ai_interpretation() -> None:
    runtime_source = _read_source("src/atreus/execution/runtime.py")
    system_source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (ROOT / "src/atreus/system").glob("*.py")
    )

    assert "RequestInterpretation" not in runtime_source
    assert "ApplicationAction" not in runtime_source
    assert "atreus.ai" not in system_source
    assert "AIProvider" not in system_source


def test_new_native_adapters_never_enable_shell_execution() -> None:
    launcher = _read_source(
        "src/atreus/system/windows_application_launcher.py"
    ).casefold()
    state_reader = _read_source(
        "src/atreus/system/windows_application_state_reader.py"
    ).casefold()

    assert "shell=true" not in launcher
    assert "shell=true" not in state_reader
    assert "shell=false" in launcher
    assert "shell=false" in state_reader
    assert "taskkill" not in state_reader
    assert "powershell" not in state_reader
