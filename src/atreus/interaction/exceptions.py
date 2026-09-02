"""Exceptions for foreground interaction contracts."""


class InvalidConversationalResponseError(Exception):
    """Raised when a conversational response violates its contract."""


class InvalidAssistantCapabilitySummaryError(Exception):
    """Raised when an assistant capability summary is invalid."""
