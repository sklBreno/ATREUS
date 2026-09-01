"""Exceptions raised by Core orchestration."""


class CoreException(Exception):
    """Base exception for Core orchestration failures."""


class InconsistentClassificationError(CoreException):
    """Raised when classification does not correspond to the request."""
