"""Unavailable AI Provider for deterministic local runtime use."""

from atreus.ai.exceptions import AIProviderUnavailableError
from atreus.ai.models import (
    AIProviderAvailability,
    AIProviderAvailabilityState,
    AIRequest,
    AIResponse,
)
from atreus.interfaces.ai_provider import AIProvider


class UnavailableAIAvailabilityProvider(AIProvider):
    """Expose a provider-neutral unavailable implementation."""

    def availability(self) -> AIProviderAvailability:
        """Return an immutable unavailable-provider snapshot."""
        return AIProviderAvailability(
            state=AIProviderAvailabilityState.UNAVAILABLE,
            reason_code="provider_not_configured",
        )

    def generate(self, request: AIRequest) -> AIResponse:
        """Reject generation without exposing configuration details."""
        raise AIProviderUnavailableError("AI Provider is unavailable.")
