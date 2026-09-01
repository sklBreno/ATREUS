"""Configuration loading from supported ATREUS sources."""

import os
from collections.abc import Mapping
from dataclasses import MISSING, fields
from pathlib import Path
from typing import cast

from atreus.configuration.configuration import Configuration
from atreus.configuration.exceptions import ConfigurationLoadError

type ConfigurationValue = str | bool | int

_ENVIRONMENT_VARIABLES = {
    "app_name": "ATREUS_APP_NAME",
    "version": "ATREUS_VERSION",
    "language": "ATREUS_LANGUAGE",
    "debug": "ATREUS_DEBUG",
    "log_level": "ATREUS_LOG_LEVEL",
    "working_memory_capacity": "ATREUS_WORKING_MEMORY_CAPACITY",
    "working_memory_entry_ttl_seconds": (
        "ATREUS_WORKING_MEMORY_ENTRY_TTL_SECONDS"
    ),
    "start_with_windows": "ATREUS_START_WITH_WINDOWS",
    "always_on": "ATREUS_ALWAYS_ON",
}

_BOOLEAN_FIELDS = {"debug", "start_with_windows", "always_on"}
_INTEGER_FIELDS = {
    "working_memory_capacity",
    "working_memory_entry_ttl_seconds",
}
_TRUE_VALUES = {"1", "true", "yes", "on"}
_FALSE_VALUES = {"0", "false", "no", "off"}


class ConfigurationLoader:
    """Load configuration values using the documented source priority.

    Process environment variables override values from a ``.env`` file, and
    both sources override the built-in platform defaults.
    """

    def __init__(
        self,
        env_file_path: Path | None = Path(".env"),
        environment: Mapping[str, str] | None = None,
    ) -> None:
        """Initialize the loader with injectable configuration sources.

        Args:
            env_file_path: Path to the optional ``.env`` file. Use ``None`` to
                disable file loading.
            environment: Environment variable mapping. Defaults to the current
                process environment.
        """
        self._env_file_path = env_file_path
        self._environment = os.environ if environment is None else environment

    def load(self) -> dict[str, ConfigurationValue]:
        """Load and merge all supported configuration sources.

        Returns:
            Configuration values keyed by model field name.

        Raises:
            ConfigurationLoadError: If a source cannot be read or contains an
                invalid value representation.
        """
        values = self._load_defaults()
        self._apply_source(values, self._load_env_file())
        self._apply_source(values, self._environment)
        return values

    @staticmethod
    def _load_defaults() -> dict[str, ConfigurationValue]:
        values: dict[str, ConfigurationValue] = {}

        for configuration_field in fields(Configuration):
            if configuration_field.default is MISSING:
                raise ConfigurationLoadError(
                    f"Missing default for configuration field "
                    f"'{configuration_field.name}'."
                )
            values[configuration_field.name] = cast(
                ConfigurationValue,
                configuration_field.default,
            )

        return values

    def _load_env_file(self) -> dict[str, str]:
        if self._env_file_path is None or not self._env_file_path.exists():
            return {}

        if not self._env_file_path.is_file():
            raise ConfigurationLoadError(
                f"Configuration path is not a file: {self._env_file_path}"
            )

        try:
            lines = self._env_file_path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeError) as error:
            raise ConfigurationLoadError(
                f"Unable to read configuration file: {self._env_file_path}"
            ) from error

        values: dict[str, str] = {}
        for line_number, line in enumerate(lines, start=1):
            parsed = self._parse_env_line(line, line_number)
            if parsed is not None:
                name, value = parsed
                values[name] = value

        return values

    @staticmethod
    def _parse_env_line(line: str, line_number: int) -> tuple[str, str] | None:
        stripped_line = line.strip()
        if not stripped_line or stripped_line.startswith("#"):
            return None

        if stripped_line.startswith("export "):
            stripped_line = stripped_line.removeprefix("export ").lstrip()

        name, separator, value = stripped_line.partition("=")
        if not separator or not name.strip():
            raise ConfigurationLoadError(f"Invalid .env entry at line {line_number}.")

        normalized_value = value.strip()
        if (
            len(normalized_value) >= 2
            and normalized_value[0] == normalized_value[-1]
            and normalized_value[0] in {'"', "'"}
        ):
            normalized_value = normalized_value[1:-1]

        return name.strip(), normalized_value

    @staticmethod
    def _apply_source(
        values: dict[str, ConfigurationValue],
        source: Mapping[str, str],
    ) -> None:
        for field_name, environment_name in _ENVIRONMENT_VARIABLES.items():
            if environment_name in source:
                values[field_name] = ConfigurationLoader._parse_value(
                    field_name,
                    source[environment_name],
                )

    @staticmethod
    def _parse_value(field_name: str, value: str) -> ConfigurationValue:
        if field_name not in _BOOLEAN_FIELDS:
            if field_name not in _INTEGER_FIELDS:
                return value
            try:
                return int(value)
            except ValueError as error:
                environment_name = _ENVIRONMENT_VARIABLES[field_name]
                raise ConfigurationLoadError(
                    f"Invalid integer value for {environment_name}: {value!r}."
                ) from error

        normalized_value = value.strip().lower()
        if normalized_value in _TRUE_VALUES:
            return True
        if normalized_value in _FALSE_VALUES:
            return False

        environment_name = _ENVIRONMENT_VARIABLES[field_name]
        raise ConfigurationLoadError(
            f"Invalid boolean value for {environment_name}: {value!r}."
        )
