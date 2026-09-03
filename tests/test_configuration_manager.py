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
            "ATREUS_WORKING_MEMORY_CAPACITY": "24",
            "ATREUS_WORKING_MEMORY_ENTRY_TTL_SECONDS": "600",
            "ATREUS_CONVERSATION_HISTORY_MAX_EXCHANGES": "4",
            "ATREUS_CONVERSATION_HISTORY_MAX_CHARACTERS": "9000",
            "ATREUS_AI_ENABLED": "true",
            "ATREUS_AI_MODEL": "test-model",
            "ATREUS_AI_TIMEOUT_SECONDS": "20",
            "ATREUS_CONFIRMATION_TTL_SECONDS": "75",
            "ATREUS_PERMISSION_GRANTS": "application.read",
        },
    )

    configuration = ConfigurationManager(loader=loader).load()

    assert configuration.language == "en-US"
    assert configuration.always_on is False
    assert configuration.working_memory_capacity == 24
    assert configuration.working_memory_entry_ttl_seconds == 600
    assert configuration.conversation_history_max_exchanges == 4
    assert configuration.conversation_history_max_characters == 9000
    assert configuration.ai_enabled is True
    assert configuration.ai_model == "test-model"
    assert configuration.ai_timeout_seconds == 20
    assert configuration.confirmation_ttl_seconds == 75
    assert configuration.permission_grants == ("application.read",)


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
