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
        "working_memory_capacity": 64,
        "working_memory_entry_ttl_seconds": 1800,
        "start_with_windows": True,
        "always_on": True,
    }


def test_loader_loads_process_environment_values() -> None:
    environment = {
        "ATREUS_LANGUAGE": "en-US",
        "ATREUS_DEBUG": "false",
        "ATREUS_LOG_LEVEL": "DEBUG",
        "ATREUS_WORKING_MEMORY_CAPACITY": "32",
        "ATREUS_WORKING_MEMORY_ENTRY_TTL_SECONDS": "900",
    }

    values = ConfigurationLoader(
        env_file_path=None,
        environment=environment,
    ).load()

    assert values["language"] == "en-US"
    assert values["debug"] is False
    assert values["log_level"] == "DEBUG"
    assert values["working_memory_capacity"] == 32
    assert values["working_memory_entry_ttl_seconds"] == 900


def test_loader_loads_env_file_values(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            (
                "# Test configuration",
                "ATREUS_APP_NAME='ATREUS Test'",
                "ATREUS_ALWAYS_ON=off",
                "export ATREUS_START_WITH_WINDOWS=no",
                "ATREUS_WORKING_MEMORY_CAPACITY=16",
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
    assert values["working_memory_capacity"] == 16


def test_process_environment_has_priority_over_env_file(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "ATREUS_LANGUAGE=es-ES\n"
        "ATREUS_DEBUG=false\n"
        "ATREUS_WORKING_MEMORY_CAPACITY=16\n",
        encoding="utf-8",
    )
    environment = {
        "ATREUS_LANGUAGE": "pt-BR",
        "ATREUS_DEBUG": "true",
        "ATREUS_WORKING_MEMORY_CAPACITY": "32",
    }

    values = ConfigurationLoader(
        env_file_path=env_file,
        environment=environment,
    ).load()

    assert values["language"] == "pt-BR"
    assert values["debug"] is True
    assert values["working_memory_capacity"] == 32


def test_loader_rejects_invalid_boolean_value() -> None:
    loader = ConfigurationLoader(
        env_file_path=None,
        environment={"ATREUS_DEBUG": "sometimes"},
    )

    with pytest.raises(ConfigurationLoadError, match="ATREUS_DEBUG") as error:
        loader.load()

    assert isinstance(error.value, ConfigurationException)


def test_loader_rejects_invalid_integer_value() -> None:
    loader = ConfigurationLoader(
        env_file_path=None,
        environment={"ATREUS_WORKING_MEMORY_CAPACITY": "many"},
    )

    with pytest.raises(
        ConfigurationLoadError,
        match="ATREUS_WORKING_MEMORY_CAPACITY",
    ):
        loader.load()


def test_loader_rejects_malformed_env_file(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("ATREUS_DEBUG\n", encoding="utf-8")
    loader = ConfigurationLoader(env_file_path=env_file, environment={})

    with pytest.raises(ConfigurationLoadError, match="line 1"):
        loader.load()
