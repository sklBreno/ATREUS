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
