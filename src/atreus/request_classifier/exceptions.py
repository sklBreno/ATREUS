"""Exceptions raised by the ATREUS Request Classifier."""


class RequestClassificationException(Exception):
    """Base exception for request classification failures."""


class InvalidRequestError(RequestClassificationException):
    """Raised when a request cannot be classified safely."""


class ClassificationFailureError(RequestClassificationException):
    """Raised when a valid request cannot receive a supported classification."""
