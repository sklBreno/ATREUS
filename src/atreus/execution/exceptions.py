"""Exceptions raised by the Capability Runtime."""


class CapabilityRuntimeException(Exception):
    """Base exception for capability loading and invocation failures."""


class InvalidCapabilityLoadingError(CapabilityRuntimeException):
    """Raised when explicitly supplied capability implementations are invalid."""


class DuplicateCapabilityImplementationError(CapabilityRuntimeException):
    """Raised when more than one implementation uses an identifier."""


class InvalidCapabilityInvocationError(CapabilityRuntimeException):
    """Raised when an invocation violates the public contract."""


class UnsupportedExecutionDeadlineError(CapabilityRuntimeException):
    """Raised when the current Runtime cannot enforce a requested deadline."""


class UnknownRuntimeCapabilityError(CapabilityRuntimeException):
    """Raised when metadata or an implementation cannot be resolved."""


class UnavailableRuntimeCapabilityError(CapabilityRuntimeException):
    """Raised when current capability availability prevents invocation."""


class MissingCapabilityPermissionsError(CapabilityRuntimeException):
    """Raised when invocation grants omit required permissions."""


class CapabilityAIUnavailableError(CapabilityRuntimeException):
    """Raised when an AI-required capability has no available AI Provider."""
