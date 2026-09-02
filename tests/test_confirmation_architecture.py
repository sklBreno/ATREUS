"""Architecture guards for Interactive Confirmation V0."""

from inspect import signature
from pathlib import Path

from atreus.execution.runtime import InProcessCapabilityRuntime

ROOT = Path(__file__).parents[1]


def _module_source(path: str) -> str:
    """Read one project source module for a narrow dependency assertion."""
    return (ROOT / path).read_text(encoding="utf-8")


def test_execution_runtime_has_no_confirmation_dependency() -> None:
    parameters = signature(InProcessCapabilityRuntime).parameters
    source = _module_source("src/atreus/execution/runtime.py")

    assert "confirmation" not in parameters
    assert "Confirmation" not in source
    assert "InteractionLanguage" not in source


def test_system_and_memory_layers_have_no_confirmation_dependency() -> None:
    for module_path in (
        ROOT / "src/atreus/system",
        ROOT / "src/atreus/memory",
    ):
        combined_source = "\n".join(
            path.read_text(encoding="utf-8")
            for path in module_path.glob("*.py")
        )
        assert "atreus.confirmation" not in combined_source
        assert "ConfirmationCoordinator" not in combined_source


def test_decision_engine_has_no_confirmation_state_dependency() -> None:
    source = _module_source("src/atreus/decision/decision_engine.py")

    assert "ConfirmationCoordinator" not in source
    assert "PendingConfirmationExistsError" not in source
    assert ".begin(" not in source
    assert ".resolve(" not in source


def test_confirmation_domain_does_not_store_translated_prompt_text() -> None:
    source = _module_source("src/atreus/confirmation/models.py")

    assert "Você quer que" not in source
    assert "Do you want me" not in source
    assert "[sim/não]" not in source
    assert "[yes/no]" not in source


def test_confirmation_does_not_add_domain_events() -> None:
    confirmation_source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (ROOT / "src/atreus/confirmation").glob("*.py")
    )

    assert "from atreus.events" not in confirmation_source
    assert "Event(" not in confirmation_source
