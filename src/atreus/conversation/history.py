"""Bounded process-local short-term conversation history."""

from atreus.conversation.exceptions import InvalidConversationExchangeError
from atreus.conversation.models import (
    ConversationExchange,
    ConversationHistoryPolicy,
    ConversationHistorySnapshot,
)
from atreus.interfaces.clock import Clock
from atreus.interfaces.conversation_history import ConversationHistoryStore


class InMemoryConversationHistory(ConversationHistoryStore):
    """Retain complete bounded exchanges for one runtime composition."""

    def __init__(self, clock: Clock, policy: ConversationHistoryPolicy) -> None:
        """Initialize an empty history with explicit clock and limits.

        Args:
            clock: Time source used to timestamp snapshots.
            policy: Immutable retention limits for complete exchanges.
        """
        self._clock = clock
        self._policy = policy
        self._exchanges: list[ConversationExchange] = []

    def snapshot(self) -> ConversationHistorySnapshot:
        """Capture the current exchanges in oldest-to-newest order."""
        return ConversationHistorySnapshot(
            captured_at=self._clock.now(),
            exchanges=tuple(self._exchanges),
        )

    def try_append(self, exchange: ConversationExchange) -> bool:
        """Atomically append and prune one complete validated exchange.

        Args:
            exchange: Complete user and assistant turn pair.

        Returns:
            ``True`` when retained, or ``False`` when the exchange alone exceeds
            the configured character budget.

        Raises:
            InvalidConversationExchangeError: If the exchange is invalid.
        """
        if not isinstance(exchange, ConversationExchange):
            raise InvalidConversationExchangeError(
                "Conversation history requires a ConversationExchange."
            )

        exchange_size = self._exchange_size(exchange)
        if exchange_size > self._policy.max_characters:
            return False

        retained = [*self._exchanges, exchange]
        total_characters = sum(self._exchange_size(item) for item in retained)
        while (
            len(retained) > self._policy.max_exchanges
            or total_characters > self._policy.max_characters
        ):
            removed = retained.pop(0)
            total_characters -= self._exchange_size(removed)

        self._exchanges = retained
        return True

    def clear(self) -> int:
        """Remove all retained exchanges and return the previous count."""
        removed_count = len(self._exchanges)
        self._exchanges.clear()
        return removed_count

    @staticmethod
    def _exchange_size(exchange: ConversationExchange) -> int:
        return len(exchange.user_turn.content) + len(exchange.assistant_turn.content)
