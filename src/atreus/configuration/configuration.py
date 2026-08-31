"""Immutable configuration model for the ATREUS platform."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Configuration:
    """Represent the validated configuration exposed to the platform.

    This immutable object is the stable data contract provided by the
    Configuration Manager. Dedicated components handle configuration loading,
    validation, and persistence outside this model.
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
