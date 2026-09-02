"""Exceptions raised by the Interactive Confirmation boundary."""


class ConfirmationException(Exception):
    """Base exception for confirmation contract and lifecycle failures."""


class InvalidConfirmationError(ConfirmationException):
    """Raised when confirmation data violates the V0 contract."""


class PendingConfirmationExistsError(ConfirmationException):
    """Raised when a valid pending confirmation already owns the V0 slot."""
