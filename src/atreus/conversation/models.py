"""Immutable contracts for short-term conversational context."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID

from atreus.conversation.exceptions import (
    InvalidConversationExchangeError,
    InvalidConversationHistoryPolicyError,
    InvalidConversationHistorySnapshotError,
    InvalidConversationTurnError,
)
from atreus.interaction.models import InteractionLanguage


class ConversationRole(StrEnum):
    """Identify one supported role in conversational history."""

    USER = "USER"
    ASSISTANT = "ASSISTANT"


@dataclass(frozen=True, slots=True)
class ConversationTurn:
    """Represent one immutable conversational message."""

    turn_id: UUID
    request_id: UUID
    role: ConversationRole
    content: str = field(repr=False)
    language: InteractionLanguage
    created_at: datetime

    def __post_init__(self) -> None:
        """Validate identity, role, content, language, and creation time."""
        if not isinstance(self.turn_id, UUID) or not isinstance(
            self.request_id,
            UUID,
        ):
            raise InvalidConversationTurnError(
                "Conversation turn identifiers must be UUIDs."
            )
        if not isinstance(self.role, ConversationRole):
            raise InvalidConversationTurnError("Conversation turn role is invalid.")
        if not isinstance(self.content, str) or not self.content.strip():
            raise InvalidConversationTurnError(
                "Conversation turn content must be non-empty."
            )
        if any(
            ord(character) < 32 and character not in "\n\t"
            for character in self.content
        ):
            raise InvalidConversationTurnError(
                "Conversation turn content contains invalid control characters."
            )
        if not isinstance(self.language, InteractionLanguage):
            raise InvalidConversationTurnError(
                "Conversation turn language is invalid."
            )
        if (
            not isinstance(self.created_at, datetime)
            or self.created_at.tzinfo is None
            or self.created_at.utcoffset() is None
        ):
            raise InvalidConversationTurnError(
                "Conversation turn created_at must be timezone-aware."
            )
        object.__setattr__(self, "created_at", self.created_at.astimezone(UTC))


@dataclass(frozen=True, slots=True)
class ConversationExchange:
    """Represent one complete user and assistant conversational exchange."""

    user_turn: ConversationTurn
    assistant_turn: ConversationTurn

    def __post_init__(self) -> None:
        """Validate roles, correlation, language, and chronological order."""
        if not isinstance(self.user_turn, ConversationTurn) or not isinstance(
            self.assistant_turn,
            ConversationTurn,
        ):
            raise InvalidConversationExchangeError(
                "Conversation exchange requires two conversation turns."
            )
        if self.user_turn.role is not ConversationRole.USER:
            raise InvalidConversationExchangeError(
                "Conversation exchange must begin with a user turn."
            )
        if self.assistant_turn.role is not ConversationRole.ASSISTANT:
            raise InvalidConversationExchangeError(
                "Conversation exchange must end with an assistant turn."
            )
        if self.user_turn.request_id != self.assistant_turn.request_id:
            raise InvalidConversationExchangeError(
                "Conversation exchange request identities must match."
            )
        if self.user_turn.language is not self.assistant_turn.language:
            raise InvalidConversationExchangeError(
                "Conversation exchange languages must match."
            )
        if self.user_turn.created_at > self.assistant_turn.created_at:
            raise InvalidConversationExchangeError(
                "Conversation user turn must not follow the assistant turn."
            )


@dataclass(frozen=True, slots=True)
class ConversationHistorySnapshot:
    """Represent a stable oldest-first view of recent conversation."""

    captured_at: datetime
    exchanges: tuple[ConversationExchange, ...]

    def __post_init__(self) -> None:
        """Validate the snapshot timestamp and immutable exchange collection."""
        if not isinstance(self.exchanges, tuple) or any(
            not isinstance(exchange, ConversationExchange)
            for exchange in self.exchanges
        ):
            raise InvalidConversationHistorySnapshotError(
                "Conversation history exchanges must be an immutable tuple."
            )
        if (
            not isinstance(self.captured_at, datetime)
            or self.captured_at.tzinfo is None
            or self.captured_at.utcoffset() is None
        ):
            raise InvalidConversationHistorySnapshotError(
                "Conversation history captured_at must be timezone-aware."
            )
        object.__setattr__(self, "captured_at", self.captured_at.astimezone(UTC))


@dataclass(frozen=True, slots=True)
class ConversationHistoryPolicy:
    """Provide immutable exchange-count and character limits."""

    max_exchanges: int
    max_characters: int

    def __post_init__(self) -> None:
        """Validate positive exact-integer policy limits."""
        if type(self.max_exchanges) is not int or self.max_exchanges <= 0:
            raise InvalidConversationHistoryPolicyError(
                "Conversation history max_exchanges must be a positive integer."
            )
        if type(self.max_characters) is not int or self.max_characters <= 0:
            raise InvalidConversationHistoryPolicyError(
                "Conversation history max_characters must be a positive integer."
            )
