"""Exceptions for provider-neutral application action contracts."""


class ApplicationActionException(Exception):
    """Base exception for application action contract failures."""


class InvalidApplicationActionError(ApplicationActionException):
    """Raised when an application action or definition is invalid."""
