"""Tests for configuration validation rules."""

import pytest

from atreus.configuration.exceptions import ConfigurationValidationError
from atreus.configuration.loader import ConfigurationLoader
from atreus.configuration.validator import ConfigurationValidator


def _valid_values() -> dict[str, object]:
    return ConfigurationLoader(env_file_path=None, environment={}).load()


def test_validator_accepts_valid_configuration() -> None:
    ConfigurationValidator().validate(_valid_values())


@pytest.mark.parametrize(
    ("field_name", "invalid_value"),
    (
        ("app_name", ""),
        ("version", "   "),
        ("language", ""),
        ("debug", "true"),
        ("start_with_windows", 1),
        ("always_on", None),
        ("log_level", "TRACE"),
        ("working_memory_capacity", 0),
        ("working_memory_entry_ttl_seconds", -1),
        ("working_memory_capacity", True),
        ("ai_enabled", "true"),
        ("ai_timeout_seconds", 0),
        ("ai_timeout_seconds", True),
        ("confirmation_ttl_seconds", 0),
        ("confirmation_ttl_seconds", True),
    ),
)
def test_validator_rejects_invalid_values(
    field_name: str,
    invalid_value: object,
) -> None:
    values: dict[str, object] = _valid_values()
    values[field_name] = invalid_value

    with pytest.raises(ConfigurationValidationError):
        ConfigurationValidator().validate(values)


def test_validator_rejects_missing_field() -> None:
    values = _valid_values()
    del values["language"]

    with pytest.raises(ConfigurationValidationError, match="Missing"):
        ConfigurationValidator().validate(values)


def test_validator_rejects_unexpected_field() -> None:
    values: dict[str, object] = _valid_values()
    values["future_setting"] = True

    with pytest.raises(ConfigurationValidationError, match="Unexpected"):
        ConfigurationValidator().validate(values)


def test_validator_requires_model_only_when_ai_is_enabled() -> None:
    disabled_values: dict[str, object] = _valid_values()
    ConfigurationValidator().validate(disabled_values)

    enabled_values = dict(disabled_values)
    enabled_values["ai_enabled"] = True

    with pytest.raises(ConfigurationValidationError, match="ai_model"):
        ConfigurationValidator().validate(enabled_values)


def test_validator_accepts_ollama_without_openai_model() -> None:
    values: dict[str, object] = _valid_values()
    values["ai_enabled"] = True
    values["ai_provider"] = "ollama"

    ConfigurationValidator().validate(values)


@pytest.mark.parametrize("provider", ("OpenAI", "local", ""))
def test_validator_rejects_unknown_ai_provider(provider: str) -> None:
    values: dict[str, object] = _valid_values()
    values["ai_provider"] = provider

    with pytest.raises(ConfigurationValidationError, match="provider"):
        ConfigurationValidator().validate(values)


@pytest.mark.parametrize(
    "base_url",
    (
        "https://localhost:11434",
        "http://example.com:11434",
        "http://localhost:11434/api",
        "http://user:password@localhost:11434",
        "http://localhost:11434?target=other",
        "http://localhost",
        " http://localhost:11434",
    ),
)
def test_validator_rejects_non_local_or_ambiguous_ollama_url(
    base_url: str,
) -> None:
    values: dict[str, object] = _valid_values()
    values["ollama_base_url"] = base_url

    with pytest.raises(ConfigurationValidationError, match="ollama_base_url"):
        ConfigurationValidator().validate(values)


@pytest.mark.parametrize(
    "model",
    ("", "qwen 3", " qwen3:8b", "qwen3:8b ", "qwen3:@latest"),
)
def test_validator_rejects_invalid_ollama_model(model: str) -> None:
    values: dict[str, object] = _valid_values()
    values["ollama_model"] = model

    with pytest.raises(ConfigurationValidationError, match="ollama_model"):
        ConfigurationValidator().validate(values)


@pytest.mark.parametrize(
    "permission_grants",
    (
        ("application.read", "application.read"),
        ("application.read", ""),
        (" application.read",),
        ("application.read ",),
        ("application.read", 1),
    ),
)
def test_validator_rejects_invalid_permission_grants(
    permission_grants: tuple[object, ...],
) -> None:
    values = _valid_values()
    values["permission_grants"] = permission_grants

    with pytest.raises(ConfigurationValidationError, match="permission grants"):
        ConfigurationValidator().validate(values)
