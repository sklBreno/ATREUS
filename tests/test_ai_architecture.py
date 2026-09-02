"""Architecture guards for the bounded AI Provider V0 integration."""

from inspect import signature
from pathlib import Path

from atreus.execution.runtime import InProcessCapabilityRuntime

ROOT = Path(__file__).parents[1]


def test_capability_runtime_has_no_ai_generation_or_interpretation_dependency() -> None:
    parameters = signature(InProcessCapabilityRuntime).parameters
    source = (ROOT / "src/atreus/execution/runtime.py").read_text(encoding="utf-8")

    assert "ai_provider" not in parameters
    assert "request_interpreter" not in parameters
    assert "interfaces.ai_provider" not in source
    assert "RequestInterpretation" not in source


def test_system_layer_has_no_ai_or_openai_dependency() -> None:
    system_source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (ROOT / "src/atreus/system").glob("*.py")
    )

    assert "openai" not in system_source.casefold()
    assert "AIProvider" not in system_source
    assert "RequestInterpreter" not in system_source


def test_openai_sdk_is_isolated_to_concrete_adapter() -> None:
    importing_files = tuple(
        path.relative_to(ROOT).as_posix()
        for path in (ROOT / "src").rglob("*.py")
        if "from openai import" in path.read_text(encoding="utf-8")
    )

    assert importing_files == ("src/atreus/ai/openai_provider.py",)


def test_secret_name_is_absent_from_public_configuration_artifacts() -> None:
    public_artifacts = (
        ROOT / ".env.example",
        ROOT / "src/atreus/configuration/configuration.py",
        ROOT / "src/atreus/configuration/loader.py",
        ROOT / "src/atreus/configuration/validator.py",
    )
    combined = "\n".join(
        path.read_text(encoding="utf-8") for path in public_artifacts
    )

    assert "ATREUS_OPENAI_API_KEY" not in combined
