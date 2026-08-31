"""Tests for configuration validation rules."""

import pytest

from atreus.configuration.exceptions import ConfigurationValidationError
from atreus.configuration.loader import ConfigurationLoader
from atreus.configuration.validator import ConfigurationValidator


def _valid_values() -> dict[str, str | bool]:
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
