"""Provider-neutral boundaries for short-term conversation history."""

from abc import ABC, abstractmethod

from atreus.conversation.models import (
    ConversationExchange,
    ConversationHistorySnapshot,
)


class ConversationHistoryProvider(ABC):
    """Provide stable immutable views of recent conversation."""

    @abstractmethod
    def snapshot(self) -> ConversationHistorySnapshot:
        """Capture the current oldest-first conversation history."""


class ConversationHistoryStore(ConversationHistoryProvider, ABC):
    """Store bounded complete exchanges for one process composition."""

    @abstractmethod
    def try_append(self, exchange: ConversationExchange) -> bool:
        """Append one complete exchange when it fits the configured policy."""

    @abstractmethod
    def clear(self) -> int:
        """Remove every retained exchange and return the number removed."""
