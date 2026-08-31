"""Exceptions raised by the ATREUS configuration subsystem."""


class ConfigurationException(Exception):
    """Base exception for configuration subsystem failures."""


class ConfigurationLoadError(ConfigurationException):
    """Raised when a configuration source cannot be loaded."""


class ConfigurationValidationError(ConfigurationException):
    """Raised when loaded configuration values are invalid."""
