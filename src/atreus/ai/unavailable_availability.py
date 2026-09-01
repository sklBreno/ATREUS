"""Unavailable AI availability provider for deterministic local runtime use."""

from atreus.ai.models import (
    AIProviderAvailability,
    AIProviderAvailabilityState,
)
from atreus.interfaces.ai_availability import AIAvailabilityProvider


class UnavailableAIAvailabilityProvider(AIAvailabilityProvider):
    """Report that no AI Provider is configured for the current runtime."""

    def availability(self) -> AIProviderAvailability:
        """Return an immutable unavailable-provider snapshot."""
        return AIProviderAvailability(
            state=AIProviderAvailabilityState.UNAVAILABLE,
            reason_code="provider_not_configured",
        )
