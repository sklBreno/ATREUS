from dataclasses import dataclass


@dataclass
class Configuration:
    app_name: str = "ATREUS"

    version: str = "0.1.0-alpha"

    language: str = "pt-BR"

    start_with_windows: bool = True

    always_on: bool = True

    debug: bool = True

    log_level: str = "INFO"


"""Configuration model for the ATREUS platform."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Configuration:
    """Immutable representation of validated platform configuration.

    The Configuration object is the stable data contract exposed by the
    Configuration Manager to the rest of the ATREUS platform. It contains only
    validated configuration values. Loading, validation, and persistence are
    handled by dedicated configuration components.
    """

    # Application identity
    app_name: str = "ATREUS"
    version: str = "0.1.0-alpha"
    language: str = "pt-BR"

    # Runtime behavior
    debug: bool = True
    log_level: str = "INFO"

    # System behavior
    start_with_windows: bool = True
    always_on: bool = True
