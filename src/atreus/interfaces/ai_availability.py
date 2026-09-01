"""Minimal AI availability boundary used by Capability Runtime."""

from abc import ABC, abstractmethod

from atreus.ai.models import AIProviderAvailability


class AIAvailabilityProvider(ABC):
    """Provide current AI Provider availability without generating content."""

    @abstractmethod
    def availability(self) -> AIProviderAvailability:
        """Return the current provider availability."""
