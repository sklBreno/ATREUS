"""Exceptions raised by Core orchestration."""


class CoreException(Exception):
    """Base exception for Core orchestration failures."""


class InconsistentClassificationError(CoreException):
    """Raised when classification does not correspond to the request."""


class InconsistentDecisionError(CoreException):
    """Raised when a decision does not correspond to the current request."""


class InconsistentPlanError(CoreException):
    """Raised when a plan does not correspond to the current request."""
