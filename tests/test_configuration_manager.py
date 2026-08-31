"""Tests for ConfigurationManager orchestration."""

import pytest

from atreus.configuration.configuration_manager import ConfigurationManager
from atreus.configuration.exceptions import ConfigurationValidationError
from atreus.configuration.loader import ConfigurationLoader


def test_manager_creates_configuration_from_loaded_values() -> None:
    loader = ConfigurationLoader(
        env_file_path=None,
        environment={
            "ATREUS_LANGUAGE": "en-US",
            "ATREUS_ALWAYS_ON": "false",
        },
    )

    configuration = ConfigurationManager(loader=loader).load()

    assert configuration.language == "en-US"
    assert configuration.always_on is False


def test_manager_returns_same_configuration_instance() -> None:
    loader = ConfigurationLoader(env_file_path=None, environment={})
    manager = ConfigurationManager(loader=loader)

    first_configuration = manager.load()
    second_configuration = manager.load()

    assert first_configuration is second_configuration


def test_manager_does_not_expose_invalid_configuration() -> None:
    loader = ConfigurationLoader(
        env_file_path=None,
        environment={"ATREUS_LOG_LEVEL": "TRACE"},
    )
    manager = ConfigurationManager(loader=loader)

    with pytest.raises(ConfigurationValidationError, match="log level"):
        manager.load()
