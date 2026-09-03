"""Tests for the immutable Configuration model."""

from dataclasses import FrozenInstanceError

import pytest

from atreus.configuration.configuration import Configuration


def test_configuration_uses_platform_defaults() -> None:
    configuration = Configuration()

    assert configuration.app_name == "ATREUS"
    assert configuration.version == "0.1.0-alpha"
    assert configuration.language == "pt-BR"
    assert configuration.debug is True
    assert configuration.log_level == "INFO"
    assert configuration.working_memory_capacity == 64
    assert configuration.working_memory_entry_ttl_seconds == 1800
    assert configuration.ai_enabled is False
    assert configuration.ai_provider == "openai"
    assert configuration.ai_model == ""
    assert configuration.ai_timeout_seconds == 30
    assert configuration.ollama_base_url == "http://localhost:11434"
    assert configuration.ollama_model == "qwen3:8b"
    assert configuration.confirmation_ttl_seconds == 120
    assert configuration.start_with_windows is True
    assert configuration.always_on is True


def test_configuration_is_immutable_and_uses_slots() -> None:
    configuration = Configuration()

    with pytest.raises(FrozenInstanceError):
        configuration.debug = False  # type: ignore[misc]

    assert not hasattr(configuration, "__dict__")


def test_configuration_contains_no_openai_credential() -> None:
    configuration = Configuration()

    assert not hasattr(configuration, "openai_api_key")
    assert "API_KEY" not in repr(configuration)
