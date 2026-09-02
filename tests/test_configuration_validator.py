"""Tests for configuration validation rules."""

import pytest

from atreus.configuration.exceptions import ConfigurationValidationError
from atreus.configuration.loader import ConfigurationLoader
from atreus.configuration.validator import ConfigurationValidator


def _valid_values() -> dict[str, str | bool | int]:
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
