"""Exceptions raised by context contracts and providers."""


class ContextEngineException(Exception):
    """Base exception for context contracts and future engine failures."""


class InvalidContextSnapshotError(ContextEngineException):
    """Raised when a context snapshot violates its immutable contract."""
