"""Normalized exceptions raised by the System Layer."""


class SystemLayerException(Exception):
    """Base exception for controlled system-boundary failures."""


class InvalidSystemOperationError(SystemLayerException):
    """Raised when a system operation contract is invalid."""


class SystemPermissionDeniedError(SystemLayerException):
    """Raised when required operation permission is absent."""


class SystemOperationCancelledError(SystemLayerException):
    """Raised when cooperative cancellation precedes an operation."""
