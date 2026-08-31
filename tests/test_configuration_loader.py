"""Tests for configuration source loading and priority resolution."""

from pathlib import Path

import pytest

from atreus.configuration.exceptions import (
    ConfigurationException,
    ConfigurationLoadError,
)
from atreus.configuration.loader import ConfigurationLoader


def test_loader_returns_default_configuration_values() -> None:
    values = ConfigurationLoader(env_file_path=None, environment={}).load()

    assert values == {
        "app_name": "ATREUS",
        "version": "0.1.0-alpha",
        "language": "pt-BR",
        "debug": True,
        "log_level": "INFO",
        "start_with_windows": True,
        "always_on": True,
    }


def test_loader_loads_process_environment_values() -> None:
    environment = {
        "ATREUS_LANGUAGE": "en-US",
        "ATREUS_DEBUG": "false",
        "ATREUS_LOG_LEVEL": "DEBUG",
    }

    values = ConfigurationLoader(
        env_file_path=None,
        environment=environment,
    ).load()

    assert values["language"] == "en-US"
    assert values["debug"] is False
    assert values["log_level"] == "DEBUG"


def test_loader_loads_env_file_values(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            (
                "# Test configuration",
                "ATREUS_APP_NAME='ATREUS Test'",
                "ATREUS_ALWAYS_ON=off",
                "export ATREUS_START_WITH_WINDOWS=no",
            )
        ),
        encoding="utf-8",
    )

    values = ConfigurationLoader(
        env_file_path=env_file,
        environment={},
    ).load()

    assert values["app_name"] == "ATREUS Test"
    assert values["always_on"] is False
    assert values["start_with_windows"] is False


def test_process_environment_has_priority_over_env_file(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "ATREUS_LANGUAGE=es-ES\nATREUS_DEBUG=false\n",
        encoding="utf-8",
    )
    environment = {
        "ATREUS_LANGUAGE": "pt-BR",
        "ATREUS_DEBUG": "true",
    }

    values = ConfigurationLoader(
        env_file_path=env_file,
        environment=environment,
    ).load()

    assert values["language"] == "pt-BR"
    assert values["debug"] is True


def test_loader_rejects_invalid_boolean_value() -> None:
    loader = ConfigurationLoader(
        env_file_path=None,
        environment={"ATREUS_DEBUG": "sometimes"},
    )

    with pytest.raises(ConfigurationLoadError, match="ATREUS_DEBUG") as error:
        loader.load()

    assert isinstance(error.value, ConfigurationException)


def test_loader_rejects_malformed_env_file(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("ATREUS_DEBUG\n", encoding="utf-8")
    loader = ConfigurationLoader(env_file_path=env_file, environment={})

    with pytest.raises(ConfigurationLoadError, match="line 1"):
        loader.load()
