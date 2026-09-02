"""Boundary for stateless, non-executive conversational responses."""

from abc import ABC, abstractmethod

from atreus.interaction.models import ConversationalResponse, InteractionLanguage
from atreus.shared.request import Request


class ConversationResponder(ABC):
    """Produce one text response without planning or executing work."""

    @abstractmethod
    def respond(
        self,
        request: Request,
        language: InteractionLanguage,
    ) -> ConversationalResponse:
        """Return one validated response for the current request only."""
