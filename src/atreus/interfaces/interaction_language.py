"""Boundary for deterministic interaction-language resolution."""

from abc import ABC, abstractmethod

from atreus.interaction.models import InteractionLanguage


class InteractionLanguageResolver(ABC):
    """Resolve one supported interaction language without AI inference."""

    @abstractmethod
    def resolve(self, content: str) -> InteractionLanguage:
        """Return the supported language for one request content value."""
