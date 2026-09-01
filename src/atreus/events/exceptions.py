"""Exceptions raised by the ATREUS Event Bus."""


class EventBusException(Exception):
    """Base exception for Event Bus contract failures."""


class InvalidEventError(EventBusException):
    """Raised when a published object is not a valid event."""


class InvalidEventHandlerError(EventBusException):
    """Raised when a subscription handler is invalid."""


class UnknownSubscriptionError(EventBusException):
    """Raised when a subscription is not registered with the Event Bus."""


class EventBusInternalError(EventBusException):
    """Raised when the Event Bus cannot preserve its internal contract."""
