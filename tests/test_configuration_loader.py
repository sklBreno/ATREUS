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
        "ai_enabled": False,
        "ai_model": "",
        "ai_timeout_seconds": 30,
        "confirmation_ttl_seconds": 120,
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
        "ATREUS_AI_ENABLED": "true",
        "ATREUS_AI_MODEL": "test-model",
        "ATREUS_AI_TIMEOUT_SECONDS": "12",
        "ATREUS_CONFIRMATION_TTL_SECONDS": "90",
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
    assert values["ai_enabled"] is True
    assert values["ai_model"] == "test-model"
    assert values["ai_timeout_seconds"] == 12
    assert values["confirmation_ttl_seconds"] == 90


def test_loader_never_exposes_openai_api_key() -> None:
    values = ConfigurationLoader(
        env_file_path=None,
        environment={"ATREUS_OPENAI_API_KEY": "private-key"},
    ).load()

    assert "openai_api_key" not in values
    assert "private-key" not in repr(values)


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
                "ATREUS_CONFIRMATION_TTL_SECONDS=60",
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
    assert values["confirmation_ttl_seconds"] == 60


def test_process_environment_has_priority_over_env_file(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "ATREUS_LANGUAGE=es-ES\n"
        "ATREUS_DEBUG=false\n"
        "ATREUS_WORKING_MEMORY_CAPACITY=16\n"
        "ATREUS_CONFIRMATION_TTL_SECONDS=60\n",
        encoding="utf-8",
    )
    environment = {
        "ATREUS_LANGUAGE": "pt-BR",
        "ATREUS_DEBUG": "true",
        "ATREUS_WORKING_MEMORY_CAPACITY": "32",
        "ATREUS_CONFIRMATION_TTL_SECONDS": "90",
    }

    values = ConfigurationLoader(
        env_file_path=env_file,
        environment=environment,
    ).load()

    assert values["language"] == "pt-BR"
    assert values["debug"] is True
    assert values["working_memory_capacity"] == 32
    assert values["confirmation_ttl_seconds"] == 90


def test_loader_rejects_invalid_boolean_value() -> None:
    loader = ConfigurationLoader(
        env_file_path=None,
        environment={"ATREUS_DEBUG": "sometimes"},
    )

    with pytest.raises(ConfigurationLoadError, match="ATREUS_DEBUG") as error:
        loader.load()

    assert isinstance(error.value, ConfigurationException)


@pytest.mark.parametrize(
    "environment_name",
    (
        "ATREUS_WORKING_MEMORY_CAPACITY",
        "ATREUS_CONFIRMATION_TTL_SECONDS",
    ),
)
def test_loader_rejects_invalid_integer_value(environment_name: str) -> None:
    loader = ConfigurationLoader(
        env_file_path=None,
        environment={environment_name: "many"},
    )

    with pytest.raises(
        ConfigurationLoadError,
        match=environment_name,
    ):
        loader.load()


def test_loader_rejects_malformed_env_file(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("ATREUS_DEBUG\n", encoding="utf-8")
    loader = ConfigurationLoader(env_file_path=env_file, environment={})

    with pytest.raises(ConfigurationLoadError, match="line 1"):
        loader.load()
