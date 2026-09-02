"""Provider-neutral boundary for bounded AI generation."""

from abc import abstractmethod

from atreus.ai.models import AIRequest, AIResponse
from atreus.interfaces.ai_availability import AIAvailabilityProvider


class AIProvider(AIAvailabilityProvider):
    """Generate one bounded response behind a replaceable provider contract."""

    @abstractmethod
    def generate(self, request: AIRequest) -> AIResponse:
        """Generate a normalized response for one validated AI request."""
