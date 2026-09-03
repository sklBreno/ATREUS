"""Exceptions raised by the short-term conversation history boundary."""


class ConversationHistoryException(Exception):
    """Base exception for conversation history failures."""


class InvalidConversationTurnError(ConversationHistoryException):
    """Raised when a conversation turn violates its contract."""


class InvalidConversationExchangeError(ConversationHistoryException):
    """Raised when a conversation exchange violates its contract."""


class InvalidConversationHistorySnapshotError(ConversationHistoryException):
    """Raised when a conversation history snapshot is invalid."""


class InvalidConversationHistoryPolicyError(ConversationHistoryException):
    """Raised when conversation history policy values are invalid."""
