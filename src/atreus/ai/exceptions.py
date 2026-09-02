"""Normalized exceptions for bounded AI Provider operations."""


class AIProviderException(Exception):
    """Base exception for provider-neutral AI failures."""


class InvalidAIRequestError(AIProviderException):
    """Raised when an AI request violates the public contract."""


class InvalidAIResponseError(AIProviderException):
    """Raised when a normalized AI response violates its contract."""


class AIProviderUnavailableError(AIProviderException):
    """Raised when no AI Provider can serve the request."""


class AIAuthenticationError(AIProviderException):
    """Raised when provider authentication fails."""


class AIRateLimitError(AIProviderException):
    """Raised when the provider rejects a request due to rate limits."""


class AIRequestTimeoutError(AIProviderException):
    """Raised when a bounded provider request exceeds its deadline."""


class AINetworkError(AIProviderException):
    """Raised when provider communication fails."""


class AIMalformedProviderResponseError(AIProviderException):
    """Raised when a provider response cannot be normalized."""


class AIInternalProviderError(AIProviderException):
    """Raised for an unexpected sanitized provider failure."""


class RequestInterpretationException(Exception):
    """Base exception for bounded request interpretation failures."""


class InvalidRequestInterpretationError(RequestInterpretationException):
    """Raised when structured interpretation data is invalid."""


class InterpretationTargetUnavailableError(RequestInterpretationException):
    """Raised when the approved capability target is unavailable."""
