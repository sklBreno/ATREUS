"""Configuration contracts exposed to ATREUS consumers."""

from abc import ABC, abstractmethod

from atreus.configuration.configuration import Configuration


class ConfigurationProvider(ABC):
    """Define access to the platform's validated configuration."""

    @abstractmethod
    def load(self) -> Configuration:
        """Return the validated configuration for the current execution.

        Returns:
            The immutable platform configuration.
        """
