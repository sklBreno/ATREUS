"""Application bootstrap orchestration for the ATREUS foundation runtime."""

from atreus.configuration.configuration import Configuration
from atreus.configuration.configuration_manager import ConfigurationManager
from atreus.interfaces.configuration import ConfigurationProvider


class Bootstrap:
    """Initialize the foundation services required by the ATREUS runtime."""

    def __init__(
        self,
        configuration_provider: ConfigurationProvider | None = None,
    ) -> None:
        """Initialize Bootstrap with an injectable configuration provider.

        Args:
            configuration_provider: Provider for the validated application
                configuration.
        """
        self._configuration_provider = (
            configuration_provider
            if configuration_provider is not None
            else ConfigurationManager()
        )

    def run(self) -> Configuration:
        """Initialize and return the foundation runtime configuration.

        Returns:
            The validated, immutable application configuration.
        """
        return self._configuration_provider.load()
