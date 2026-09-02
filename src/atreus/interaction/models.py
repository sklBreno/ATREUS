"""Immutable contracts for supported foreground interaction languages."""

from enum import StrEnum


class InteractionLanguage(StrEnum):
    """Identify one language supported by the interactive V0 boundary."""

    PT_BR = "pt-BR"
    EN_US = "en-US"
