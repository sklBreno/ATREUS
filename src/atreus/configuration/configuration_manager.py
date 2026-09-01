"""Central configuration service for the ATREUS platform."""

from typing import cast

from atreus.configuration.configuration import Configuration
from atreus.configuration.loader import ConfigurationLoader
from atreus.configuration.validator import ConfigurationValidator
from atreus.interfaces.configuration import ConfigurationProvider


class ConfigurationManager(ConfigurationProvider):
    """Coordinate loading, validation, and configuration availability."""

    def __init__(
        self,
        loader: ConfigurationLoader | None = None,
        validator: ConfigurationValidator | None = None,
    ) -> None:
        """Initialize the manager with injectable configuration components.

        Args:
            loader: Component used to load configuration values.
            validator: Component used to validate loaded values.
        """
        self._loader = loader or ConfigurationLoader()
        self._validator = validator or ConfigurationValidator()
        self._configuration: Configuration | None = None

    def load(self) -> Configuration:
        """Load and expose the platform's immutable configuration.

        The first call creates the configuration object. Later calls return the
        same object to preserve a single source of truth during execution.

        Returns:
            The validated, immutable platform configuration.
        """
        if self._configuration is not None:
            return self._configuration

        values = self._loader.load()
        self._validator.validate(values)

        self._configuration = Configuration(
            app_name=cast(str, values["app_name"]),
            version=cast(str, values["version"]),
            language=cast(str, values["language"]),
            debug=cast(bool, values["debug"]),
            log_level=cast(str, values["log_level"]),
            working_memory_capacity=cast(
                int,
                values["working_memory_capacity"],
            ),
            working_memory_entry_ttl_seconds=cast(
                int,
                values["working_memory_entry_ttl_seconds"],
            ),
            start_with_windows=cast(bool, values["start_with_windows"]),
            always_on=cast(bool, values["always_on"]),
        )
        return self._configuration
