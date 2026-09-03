"""Validation for loaded ATREUS configuration values."""

import re
from collections.abc import Mapping
from urllib.parse import urlsplit

from atreus.configuration.exceptions import ConfigurationValidationError

_EXPECTED_TYPES: dict[
    str,
    type[str] | type[bool] | type[int] | type[tuple],
] = {
    "app_name": str,
    "version": str,
    "language": str,
    "debug": bool,
    "log_level": str,
    "working_memory_capacity": int,
    "working_memory_entry_ttl_seconds": int,
    "conversation_history_max_exchanges": int,
    "conversation_history_max_characters": int,
    "ai_enabled": bool,
    "ai_provider": str,
    "ai_model": str,
    "ai_timeout_seconds": int,
    "ollama_base_url": str,
    "ollama_model": str,
    "confirmation_ttl_seconds": int,
    "personal_profile_enabled": bool,
    "personal_profile_projection_max_characters": int,
    "personal_profile_clear_confirmation_ttl_seconds": int,
    "permission_grants": tuple,
    "start_with_windows": bool,
    "always_on": bool,
}

_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
_AI_PROVIDERS = {"openai", "ollama"}
_LOCAL_OLLAMA_HOSTS = {"localhost", "127.0.0.1"}
_OLLAMA_MODEL_PATTERN = re.compile(
    r"[A-Za-z0-9][A-Za-z0-9._/-]*(?::[A-Za-z0-9._-]+)?"
)


class ConfigurationValidator:
    """Validate loaded values before a Configuration object is created."""

    def validate(self, values: Mapping[str, object]) -> None:
        """Validate configuration field presence, types, and supported values.

        Args:
            values: Loaded configuration values keyed by model field name.

        Raises:
            ConfigurationValidationError: If any configuration value is
                missing, unexpected, or invalid.
        """
        self._validate_fields(values)
        self._validate_types(values)
        self._validate_strings(values)
        self._validate_log_level(values)
        self._validate_positive_integers(values)
        self._validate_permission_grants(values)
        self._validate_ai_configuration(values)

    @staticmethod
    def _validate_fields(values: Mapping[str, object]) -> None:
        expected_fields = set(_EXPECTED_TYPES)
        actual_fields = set(values)

        missing_fields = sorted(expected_fields - actual_fields)
        if missing_fields:
            raise ConfigurationValidationError(
                f"Missing configuration fields: {', '.join(missing_fields)}."
            )

        unexpected_fields = sorted(actual_fields - expected_fields)
        if unexpected_fields:
            raise ConfigurationValidationError(
                f"Unexpected configuration fields: {', '.join(unexpected_fields)}."
            )

    @staticmethod
    def _validate_types(values: Mapping[str, object]) -> None:
        for field_name, expected_type in _EXPECTED_TYPES.items():
            value = values[field_name]
            if type(value) is not expected_type:
                raise ConfigurationValidationError(
                    f"Configuration field '{field_name}' must be "
                    f"{expected_type.__name__}."
                )

    @staticmethod
    def _validate_strings(values: Mapping[str, object]) -> None:
        for field_name, expected_type in _EXPECTED_TYPES.items():
            if expected_type is str:
                value = values[field_name]
                if (
                    field_name != "ai_model"
                    and isinstance(value, str)
                    and not value.strip()
                ):
                    raise ConfigurationValidationError(
                        f"Configuration field '{field_name}' cannot be empty."
                    )

    @staticmethod
    def _validate_log_level(values: Mapping[str, object]) -> None:
        log_level = values["log_level"]
        if isinstance(log_level, str) and log_level not in _LOG_LEVELS:
            raise ConfigurationValidationError(f"Unsupported log level: {log_level!r}.")

    @staticmethod
    def _validate_positive_integers(values: Mapping[str, object]) -> None:
        for field_name in (
            "working_memory_capacity",
            "working_memory_entry_ttl_seconds",
            "conversation_history_max_exchanges",
            "conversation_history_max_characters",
            "ai_timeout_seconds",
            "confirmation_ttl_seconds",
            "personal_profile_projection_max_characters",
            "personal_profile_clear_confirmation_ttl_seconds",
        ):
            value = values[field_name]
            if isinstance(value, int) and value <= 0:
                raise ConfigurationValidationError(
                    f"Configuration field '{field_name}' must be positive."
                )

    @staticmethod
    def _validate_ai_configuration(values: Mapping[str, object]) -> None:
        provider = values["ai_provider"]
        if isinstance(provider, str) and provider not in _AI_PROVIDERS:
            raise ConfigurationValidationError(
                f"Unsupported AI provider: {provider!r}."
            )

        base_url = values["ollama_base_url"]
        if isinstance(base_url, str):
            ConfigurationValidator._validate_ollama_base_url(base_url)

        ollama_model = values["ollama_model"]
        if isinstance(ollama_model, str) and not _OLLAMA_MODEL_PATTERN.fullmatch(
            ollama_model
        ):
            raise ConfigurationValidationError(
                "Configuration field 'ollama_model' is invalid."
            )

        if values["ai_enabled"] is not True:
            return
        if provider == "openai":
            model = values["ai_model"]
            if isinstance(model, str) and not model.strip():
                raise ConfigurationValidationError(
                    "Configuration field 'ai_model' cannot be empty when the "
                    "OpenAI provider is enabled."
                )

    @staticmethod
    def _validate_ollama_base_url(base_url: str) -> None:
        try:
            parsed = urlsplit(base_url)
            port = parsed.port
        except ValueError as error:
            raise ConfigurationValidationError(
                "Configuration field 'ollama_base_url' is invalid."
            ) from error
        if (
            parsed.scheme != "http"
            or parsed.hostname not in _LOCAL_OLLAMA_HOSTS
            or parsed.username is not None
            or parsed.password is not None
            or parsed.path not in {"", "/"}
            or parsed.query
            or parsed.fragment
            or port is None
            or base_url != base_url.strip()
        ):
            raise ConfigurationValidationError(
                "Configuration field 'ollama_base_url' must identify an explicit "
                "local HTTP endpoint."
            )

    @staticmethod
    def _validate_permission_grants(values: Mapping[str, object]) -> None:
        grants = values["permission_grants"]
        if not isinstance(grants, tuple):
            return
        if any(
            not isinstance(grant, str)
            or not grant.strip()
            or grant != grant.strip()
            for grant in grants
        ):
            raise ConfigurationValidationError(
                "Configuration permission grants must be normalized strings."
            )
        if len(grants) != len(set(grants)):
            raise ConfigurationValidationError(
                "Configuration permission grants must be unique."
            )
