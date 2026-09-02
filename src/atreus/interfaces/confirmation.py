"""Boundary for bounded process-local interactive confirmation."""

from abc import ABC, abstractmethod
from uuid import UUID

from atreus.confirmation.models import (
    ConfirmationAction,
    ConfirmationResolution,
    PendingConfirmation,
)
from atreus.interaction.models import InteractionLanguage


class ConfirmationCoordinator(ABC):
    """Own one process-local pending confirmation and its single-use lifecycle."""

    @abstractmethod
    def begin(
        self,
        original_request_id: UUID,
        action: ConfirmationAction,
        language: InteractionLanguage,
    ) -> PendingConfirmation:
        """Create one pending confirmation when the slot is available."""

    @abstractmethod
    def resolve(
        self,
        response_request_id: UUID,
        content: str,
    ) -> ConfirmationResolution:
        """Resolve exact foreground input against the current pending action."""

    @abstractmethod
    def clear(self) -> bool:
        """Remove the pending confirmation and report whether one existed."""
