"""Validation for loaded ATREUS configuration values."""

from collections.abc import Mapping

from atreus.configuration.exceptions import ConfigurationValidationError

_EXPECTED_TYPES: dict[str, type[str] | type[bool] | type[int]] = {
    "app_name": str,
    "version": str,
    "language": str,
    "debug": bool,
    "log_level": str,
    "working_memory_capacity": int,
    "working_memory_entry_ttl_seconds": int,
    "ai_enabled": bool,
    "ai_model": str,
    "ai_timeout_seconds": int,
    "start_with_windows": bool,
    "always_on": bool,
}

_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}


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
            "ai_timeout_seconds",
        ):
            value = values[field_name]
            if isinstance(value, int) and value <= 0:
                raise ConfigurationValidationError(
                    f"Configuration field '{field_name}' must be positive."
                )

    @staticmethod
    def _validate_ai_configuration(values: Mapping[str, object]) -> None:
        if values["ai_enabled"] is True:
            model = values["ai_model"]
            if isinstance(model, str) and not model.strip():
                raise ConfigurationValidationError(
                    "Configuration field 'ai_model' cannot be empty when AI is enabled."
                )
